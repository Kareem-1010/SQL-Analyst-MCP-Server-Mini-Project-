"""
Route: /api/upload
Accepts CSV or Excel file, runs ingestion pipeline against the user's own database.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from services.ingestion_service import ingest_file
from db.database import get_user_engine
from auth.dependencies import get_current_user
import logging

router = APIRouter(prefix="/api", tags=["upload"])
logger = logging.getLogger(__name__)

MAX_FILE_SIZE_MB = 50


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("csv", "xlsx", "xls"):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported.")

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=413, detail=f"File too large (max {MAX_FILE_SIZE_MB}MB).")

    user_engine = get_user_engine(current_user["db_name"])
    logger.info(f"[upload] User '{current_user['username']}' uploading '{file.filename}' ({size_mb:.2f}MB)")
    result, table_name = ingest_file(content, file.filename, db_engine=user_engine)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Ingestion failed."))

    return result
