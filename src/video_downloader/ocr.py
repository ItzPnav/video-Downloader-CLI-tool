"""
OCR Engine for Video Extractor CLI.
Extracts text from images and multi-page document images using Tesseract OCR and Pillow.
Supports single image files, image lists, and directory scanning with natural sorting.
"""

import os
import re
import sys
import shutil
from pathlib import Path
from typing import Callable, List, Optional, Tuple, Union

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

from .utils import get_download_dir, safe_filename

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".gif"}


def natural_sort_key(s: str) -> list:
    """Natural alphanumeric sort key (e.g. 1.jpg, 2.jpg, 10.jpg)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)]


def find_tesseract_binary() -> Optional[str]:
    """Locate Tesseract OCR binary across standard installation paths."""
    exe = shutil.which("tesseract") or (shutil.which("tesseract.exe") if sys.platform == "win32" else None)
    if exe:
        return exe

    if sys.platform == "win32":
        search_paths = [
            Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Tesseract-OCR" / "tesseract.exe",
            Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "Tesseract-OCR" / "tesseract.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Tesseract-OCR" / "tesseract.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Tesseract-OCR" / "tesseract.exe",
            Path.home() / "scoop" / "shims" / "tesseract.exe",
            Path(os.environ.get("SystemDrive", "C:")) / "ProgramData" / "chocolatey" / "bin" / "tesseract.exe",
        ]
        for p in search_paths:
            if p.is_file():
                if PYTESSERACT_AVAILABLE:
                    pytesseract.pytesseract.tesseract_cmd = str(p)
                return str(p)
    else:
        unix_paths = [
            Path("/data/data/com.termux/files/usr/bin/tesseract"),
            Path("/usr/local/bin/tesseract"),
            Path("/usr/bin/tesseract"),
            Path("/opt/homebrew/bin/tesseract"),
        ]
        for p in unix_paths:
            if p.is_file() and os.access(p, os.X_OK):
                if PYTESSERACT_AVAILABLE:
                    pytesseract.pytesseract.tesseract_cmd = str(p)
                return str(p)

    return None


def is_tesseract_available() -> bool:
    """Check if both pytesseract and Tesseract OCR engine are installed and accessible."""
    if not PYTESSERACT_AVAILABLE or not PILLOW_AVAILABLE:
        return False
    return find_tesseract_binary() is not None


def get_tesseract_install_hint() -> str:
    """Return platform-specific installation instructions for Tesseract OCR."""
    if sys.platform == "win32":
        return (
            "Tesseract OCR is not installed or not in PATH.\n"
            "  Install on Windows via winget:\n"
            "    winget install UB-Mannheim.TesseractOCR\n"
            "  Python package: pip install pytesseract pillow"
        )
    elif "com.termux" in os.environ.get("PREFIX", ""):
        return (
            "Tesseract OCR is not installed in Termux.\n"
            "  Run: pkg install tesseract python-pillow\n"
            "  Then: pip install pytesseract"
        )
    elif sys.platform == "darwin":
        return (
            "Tesseract OCR is not installed on macOS.\n"
            "  Run: brew install tesseract\n"
            "  Then: pip install pytesseract pillow"
        )
    else:
        return (
            "Tesseract OCR is not installed on Linux.\n"
            "  Run: sudo apt install tesseract-ocr\n"
            "  Then: pip install pytesseract pillow"
        )


def extract_text_from_image(image_path: Union[str, Path], lang: str = "eng") -> str:
    """Extract text from a single image using Tesseract OCR."""
    if not PILLOW_AVAILABLE:
        raise RuntimeError("Pillow is required for OCR. Run: pip install pillow")
    if not PYTESSERACT_AVAILABLE:
        raise RuntimeError("pytesseract is required for OCR. Run: pip install pytesseract")

    tess_bin = find_tesseract_binary()
    if not tess_bin:
        raise RuntimeError(get_tesseract_install_hint())

    image_path = Path(image_path).resolve()
    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    with Image.open(image_path) as img:
        text = pytesseract.image_to_string(img, lang=lang)
    return text.strip()


def run_ocr(
    target: Union[str, Path, List[Union[str, Path]]],
    output_dir: Optional[Union[str, Path]] = None,
    lang: str = "eng",
    combine_output: bool = True,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Tuple[bool, Path, str]:
    """
    Perform OCR on a single image, list of images, or directory of images.
    
    Returns:
        (success: bool, output_path: Path, extracted_preview: str)
    """
    if not is_tesseract_available():
        raise RuntimeError(get_tesseract_install_hint())

    # Collect image paths
    image_paths: List[Path] = []
    default_name = "ocr_output"

    if isinstance(target, list):
        for item in target:
            p = Path(item).resolve()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
                image_paths.append(p)
        if image_paths:
            default_name = f"ocr_{image_paths[0].stem}"
    else:
        p = Path(target).resolve()
        if p.is_file():
            if p.suffix.lower() in IMAGE_EXTENSIONS:
                image_paths.append(p)
                default_name = f"ocr_{p.stem}"
            else:
                raise ValueError(f"File is not a supported image format: {p}")
        elif p.is_dir():
            default_name = f"ocr_{p.name}"
            for f in p.iterdir():
                if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS:
                    image_paths.append(f)
            image_paths.sort(key=lambda x: natural_sort_key(x.name))
        else:
            raise FileNotFoundError(f"Target not found: {target}")

    if not image_paths:
        raise ValueError(f"No valid image files found in target: {target}")

    # Determine output folder
    if not output_dir:
        out_base = Path(get_download_dir()) / "OCR"
    else:
        out_base = Path(output_dir).resolve()
    out_base.mkdir(parents=True, exist_ok=True)

    total = len(image_paths)
    combined_texts: List[str] = []
    created_files: List[Path] = []

    if progress_callback:
        progress_callback(5, f"Starting OCR on {total} image(s) [lang={lang}]...")

    for idx, img_path in enumerate(image_paths, start=1):
        try:
            text = extract_text_from_image(img_path, lang=lang)
            if combine_output:
                combined_texts.append(f"=== {img_path.name} ===\n{text}\n")
            else:
                out_file = out_base / f"{img_path.stem}.txt"
                out_file.write_text(text, encoding="utf-8")
                created_files.append(out_file)

            if progress_callback:
                pct = int(5 + (idx / total) * 90)
                progress_callback(pct, f"Processed ({idx}/{total}): {img_path.name}")
        except Exception as e:
            if progress_callback:
                progress_callback(int(5 + (idx / total) * 90), f"Error on {img_path.name}: {e}")

    if combine_output:
        final_output_file = out_base / f"{safe_filename(default_name)}.txt"
        full_text = "\n".join(combined_texts)
        final_output_file.write_text(full_text, encoding="utf-8")
        preview = full_text[:1000]
        if progress_callback:
            progress_callback(100, f"Saved combined OCR output: {final_output_file.name}")
        return True, final_output_file, preview
    else:
        first_file = created_files[0] if created_files else out_base
        preview_text = first_file.read_text(encoding="utf-8")[:1000] if created_files else ""
        if progress_callback:
            progress_callback(100, f"Saved {len(created_files)} text file(s) to: {out_base.name}")
        return True, out_base, preview_text
