#!/usr/bin/env python3
"""
Build script for QueryMind paper figures.
Compiles all TikZ figure files to PDF.
"""

import os
import subprocess
import sys
from pathlib import Path

def compile_figure(tex_file):
    """Compile a single TikZ figure to PDF."""
    print(f"Compiling {tex_file.name}...")
    
    try:
        result = subprocess.run(
            ["pdflatex", "--shell-escape", "--interaction=nonstopmode", str(tex_file)],
            cwd=tex_file.parent,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print(f"  ✓ {tex_file.stem}.pdf generated successfully")
            return True
        else:
            print(f"  ✗ Compilation failed:")
            print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
            return False
    
    except FileNotFoundError:
        print("  ✗ pdflatex not found. Please install LaTeX:")
        print("    - Ubuntu/Debian: apt-get install texlive-full")
        print("    - macOS: brew install --cask mactex")
        print("    - Windows: Download from https://miktex.org/download")
        return False
    except subprocess.TimeoutExpired:
        print(f"  ✗ Compilation timed out")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def cleanup_build_files(directory):
    """Remove temporary LaTeX build files."""
    extensions = [".aux", ".log", ".out", ".fls", ".fdb_latexmk"]
    for ext in extensions:
        for file in directory.glob(f"*{ext}"):
            try:
                file.unlink()
            except:
                pass

def main():
    # Get the figures directory
    script_dir = Path(__file__).parent
    figures_dir = script_dir / "figures"
    
    if not figures_dir.exists():
        print(f"Error: figures directory not found at {figures_dir}")
        sys.exit(1)
    
    # Find all TikZ figure files
    figure_files = sorted(figures_dir.glob("*.tex"))
    
    if not figure_files:
        print(f"No .tex files found in {figures_dir}")
        sys.exit(1)
    
    print(f"Found {len(figure_files)} figure(s) to compile:")
    for f in figure_files:
        print(f"  - {f.name}")
    print()
    
    # Compile each figure
    results = {}
    for tex_file in figure_files:
        results[tex_file.name] = compile_figure(tex_file)
    
    # Cleanup temporary files
    print("\nCleaning up temporary build files...")
    cleanup_build_files(figures_dir)
    
    # Summary
    print("\n" + "="*50)
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    print(f"Build Summary: {success_count}/{total_count} figures compiled successfully")
    
    if success_count == total_count:
        print("\nAll figures ready! Generated PDF files:")
        for tex_file in figure_files:
            pdf_file = tex_file.with_suffix(".pdf")
            if pdf_file.exists():
                size_kb = pdf_file.stat().st_size / 1024
                print(f"  - {pdf_file.name} ({size_kb:.1f} KB)")
        print("\nYou can now:")
        print("  1. Upload the .pdf files to Overleaf figures/ folder, OR")
        print("  2. Use \\input{figures/file.tex} in the main LaTeX document")
        sys.exit(0)
    else:
        print("\nSome figures failed to compile. Check the output above for errors.")
        sys.exit(1)

if __name__ == "__main__":
    main()
