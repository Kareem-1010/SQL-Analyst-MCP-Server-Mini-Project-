"""
Route: /api/auth
  POST /api/auth/register  — create account + per-user PostgreSQL database
  POST /api/auth/login     — verify credentials, return JWT
  GET  /api/auth/me        — return current user info from token
  POST /api/auth/refresh   — refresh access token
  POST /api/auth/logout    — logout (client-side, but for audit)
  POST /api/auth/change-password — change user password
"""
import re
import logging
import bcrypt
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from db.database import get_db, create_postgres_database, init_user_db
from db.auth_models import User
from auth.dependencies import create_access_token, get_current_user
from services.audit_service import log_audit_event

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password meets requirements:
    - At least 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    - At least 1 special character
    
    Returns:
        (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one digit"
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
        return False, "Password must contain at least one special character"
    
    return True, ""


# ── Input schemas ────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_\-\.]+$')
    password: str = Field(..., min_length=8)
    display_name: str = Field(default="", max_length=100)
    email: str = Field(default="", max_length=255)


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def _sanitise_username(username: str) -> str:
    """Lowercase, replace non-alphanumeric with underscores, limit to 50 chars."""
    cleaned = re.sub(r"[^a-z0-9_]", "_", username.strip().lower())
    # Remove leading digits
    if cleaned and cleaned[0].isdigit():
        cleaned = "u_" + cleaned
    return cleaned[:50]


def _make_db_name(username: str) -> str:
    """Generate database name from username."""
    return f"db_{username}"


# ── Register ─────────────────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
    user_agent: str = Header(default="unknown")
):
    """
    Register a new user and create their isolated PostgreSQL database.
    
    - Creates user account in central database
    - Creates isolated PostgreSQL database for user's data
    - Returns JWT token for immediate login
    """
    if not request.username or not request.password:
        raise HTTPException(status_code=400, detail="Username and password are required.")
    
    # Validate password strength
    is_valid, error_msg = _validate_password_strength(request.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    username = _sanitise_username(request.username)
    if not username or len(username) < 3:
        raise HTTPException(status_code=400, detail="Invalid username after sanitization.")

    # Check uniqueness
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        log_audit_event(
            db, username, "", "register_failure",
            status="failure",
            details={"reason": "username_exists"},
            user_agent=user_agent
        )
        raise HTTPException(status_code=409, detail="Username already taken.")

    db_name = _make_db_name(username)
    hashed = _hash_password(request.password)

    # Create PostgreSQL database for this user
    try:
        create_postgres_database(db_name)
        init_user_db(db_name)
    except Exception as e:
        logger.error(f"[auth/register] Failed to create DB for '{username}': {e}")
        log_audit_event(
            db, username, db_name, "register_failure",
            status="failure",
            details={"reason": str(e)},
            user_agent=user_agent
        )
        raise HTTPException(status_code=500, detail=f"Could not create user database: {str(e)[:100]}")

    # Persist user in central DB
    try:
        user = User(
            username=username,
            hashed_password=hashed,
            db_name=db_name,
            email=request.email or None
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        log_audit_event(
            db, username, db_name, "register_success",
            status="success",
            user_agent=user_agent
        )
        logger.info(f"[auth] Registered new user '{username}', DB: '{db_name}'")
        
    except Exception as e:
        db.rollback()
        logger.error(f"[auth/register] Failed to save user: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user account")

    token = create_access_token({"sub": username, "db": db_name})
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": username,
        "db_name": db_name,
        "display_name": user.display_name,
    }


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login")
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
    user_agent: str = Header(default="unknown")
):
    """
    Authenticate user and return JWT access token.
    Logs audit event for login success/failure.
    """
    username = _sanitise_username(request.username)
    user = db.query(User).filter(User.username == username).first()

    if not user or not _verify_password(request.password, user.hashed_password):
        log_audit_event(
            db, username, "", "login_failure",
            status="failure",
            details={"reason": "invalid_credentials"},
            user_agent=user_agent
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    log_audit_event(
        db, user.username, user.db_name, "login_success",
        status="success",
        user_agent=user_agent
    )
    logger.info(f"[auth] User '{username}' logged in successfully")
    
    token = create_access_token(
        {"sub": user.username, "db": user.db_name},
        expires_delta=timedelta(days=7)
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user.username,
        "db_name": user.db_name,
        "display_name": user.display_name,
    }


# ── Me ────────────────────────────────────────────────────────────────────────

@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    return {
        "username": current_user["username"],
        "db_name": current_user["db_name"]
    }


# ── Change Password ───────────────────────────────────────────────────────────

@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Change user password with validation.
    Requires old password for verification.
    """
    username = current_user["username"]
    user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify old password
    if not _verify_password(request.old_password, user.hashed_password):
        log_audit_event(
            db, username, user.db_name, "password_change_failure",
            status="failure",
            details={"reason": "incorrect_old_password"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )

    # Validate new password
    is_valid, error_msg = _validate_password_strength(request.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Prevent using same password
    if _verify_password(request.new_password, user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="New password must be different from current password"
        )

    # Update password
    try:
        user.hashed_password = _hash_password(request.new_password)
        db.commit()
        
        log_audit_event(
            db, username, user.db_name, "password_change_success",
            status="success"
        )
        logger.info(f"[auth] User '{username}' changed password")
        
        return {"message": "Password changed successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"[auth] Failed to change password: {e}")
        raise HTTPException(status_code=500, detail="Failed to change password")


# ── Logout (audit event) ──────────────────────────────────────────────────────

@router.post("/logout")
def logout(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Logout endpoint (for audit purposes).
    Note: Actual logout happens client-side by deleting the token.
    """
    log_audit_event(
        db,
        current_user["username"],
        current_user["db_name"],
        "logout",
        status="success"
    )
    return {"message": "Logged out successfully"}

