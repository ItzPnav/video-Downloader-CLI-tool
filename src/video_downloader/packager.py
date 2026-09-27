"""
Image Packager Engine for Video Extractor CLI.
Provides high-performance image packaging into multi-page PDF documents and CBZ archives.
Supports natural alphanumeric sorting, nested subfolder recursion, and ANSI progress logging.
"""

import os
import re
import zipfile
from pathlib import Path
from typing import Callable, List, Optional, Tuple

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


def natural_sort_key(s: str) -> list:
    """Natural numerical sorting key (e.g. 1.jpg, 2.jpg, ..., 10.jpg)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)]


def get_sorted_images_in_folder(folder_path: str | Path) -> List[Path]:
    """Return naturally sorted list of image Paths in a folder."""
    p = Path(folder_path)
    if not p.is_dir():
        return []

    images = [
        f for f in p.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    ]
    images.sort(key=lambda x: natural_sort_key(x.name))
    return images


def images_to_pdf(
    folder_path: str | Path,
    output_pdf_path: str | Path,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Tuple[bool, int]:
    """
    Bundle all image files in a folder into a single multi-page PDF using Pillow.
    Returns (success: bool, page_count: int).
    """
    if not PILLOW_AVAILABLE:
        raise RuntimeError("Pillow is required for PDF creation. Run: pip install pillow")

    folder_path = Path(folder_path)
    output_pdf_path = Path(output_pdf_path)
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    image_files = get_sorted_images_in_folder(folder_path)
    if not image_files:
        return False, 0

    if progress_callback:
        progress_callback(5, f"Reading {len(image_files)} image(s)...")

    first_image = None
    appended_images = []

    try:
        # Load and convert first image
        with Image.open(image_files[0]) as img:
            first_image = img.convert("RGB")

        total = len(image_files)
        for idx, img_path in enumerate(image_files[1:], start=2):
            try:
                with Image.open(img_path) as im:
                    appended_images.append(im.convert("RGB"))
            except Exception as e:
                if progress_callback:
                    progress_callback(int((idx / total) * 90), f"Skipping corrupt image {img_path.name}: {e}")

            if progress_callback and idx % 5 == 0:
                progress_callback(int((idx / total) * 85), f"Processing image {idx}/{total}")

        if progress_callback:
            progress_callback(90, f"Writing PDF: {output_pdf_path.name}...")

        first_image.save(
            str(output_pdf_path),
            save_all=True,
            append_images=appended_images,
        )

        page_count = 1 + len(appended_images)
        if progress_callback:
            progress_callback(100, f"Saved PDF ({page_count} pages): {output_pdf_path.name}")

        return True, page_count

    finally:
        # Explicit cleanup
        if first_image:
            try:
                first_image.close()
            except Exception:
                pass
        for im in appended_images:
            try:
                im.close()
            except Exception:
                pass


def images_to_cbz(
    folder_path: str | Path,
    output_cbz_path: str | Path,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Tuple[bool, int]:
    """
    Bundle all image files in a folder into a standard Comic Book Zip archive (.cbz).
    Returns (success: bool, page_count: int).
    """
    folder_path = Path(folder_path)
    output_cbz_path = Path(output_cbz_path)
    output_cbz_path.parent.mkdir(parents=True, exist_ok=True)

    image_files = get_sorted_images_in_folder(folder_path)
    if not image_files:
        return False, 0

    if progress_callback:
        progress_callback(10, f"Packaging {len(image_files)} image(s) to CBZ...")

    with zipfile.ZipFile(str(output_cbz_path), "w", zipfile.ZIP_DEFLATED) as zf:
        total = len(image_files)
        for idx, img_path in enumerate(image_files, start=1):
            # Pad filename in zip for viewer ordering
            arcname = f"{idx:04d}_{img_path.name}"
            zf.write(str(img_path), arcname=arcname)
            if progress_callback and (idx % 5 == 0 or idx == total):
                progress_callback(int((idx / total) * 95), f"Archiving: {img_path.name}")

    if progress_callback:
        progress_callback(100, f"Saved CBZ: {output_cbz_path.name}")

    return True, len(image_files)


def batch_pack_folders(
    root_dir: str | Path,
    output_dir: str | Path,
    format_type: str = "pdf",
    recurse: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> List[Path]:
    """
    Scan root_dir for folders containing images and convert each folder into a separate PDF or CBZ.
    """
    root = Path(root_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    format_type = format_type.lower().lstrip(".")

    target_folders = []
    if recurse:
        for dirpath, _, filenames in os.walk(root):
            if any(Path(f).suffix.lower() in IMAGE_EXTENSIONS for f in filenames):
                target_folders.append(Path(dirpath))
        target_folders.sort(key=lambda p: natural_sort_key(p.name))
    else:
        target_folders = [d for d in root.iterdir() if d.is_dir()]
        target_folders.sort(key=lambda p: natural_sort_key(p.name))

    # Also check if root itself contains images directly
    root_images = get_sorted_images_in_folder(root)
    if root_images and root not in target_folders:
        target_folders.insert(0, root)

    created_files = []
    total = len(target_folders)

    for i, folder in enumerate(target_folders, start=1):
        folder_name = folder.name if folder != root else root.name
        out_file = out / f"{folder_name}.{format_type}"

        if progress_callback:
            progress_callback(int(((i - 1) / total) * 100), f"Processing ({i}/{total}): {folder_name}")

        if format_type == "cbz":
            ok, count = images_to_cbz(folder, out_file)
        else:
            ok, count = images_to_pdf(folder, out_file)

        if ok:
            created_files.append(out_file)

    if progress_callback:
        progress_callback(100, f"Batch conversion complete: {len(created_files)} files created.")

    return created_files
