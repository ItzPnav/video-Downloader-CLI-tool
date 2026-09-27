"""
Comic & Image Gallery Scraper Engine for Video Extractor CLI.
Extracts, downloads, and organizes comic/manga chapters and image galleries from
live URLs, saved local HTML files, or local image folders with Cloudflare bypass,
User-Agent rotation, cookie file support, and optional PDF/CBZ bundling.
"""

import os
import re
import random
import http.cookiejar
import urllib.robotparser
from pathlib import Path
from typing import Callable, List, Optional, Set, Union
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False

from .utils import safe_filename, get_download_dir
from .packager import images_to_pdf, images_to_cbz


IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".bmp", ".tiff")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
]

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENTS[0],
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
}


def build_resilient_session(
    retries: int = 4,
    backoff_factor: float = 0.5,
    use_cloudscraper: bool = True,
    cookie_file: Optional[Union[str, Path]] = None,
) -> requests.Session:
    """
    Build a requests Session configured with automatic HTTP retries, exponential backoff,
    optional Cloudflare bypass via cloudscraper, and cookie file injection.
    """
    if use_cloudscraper and CLOUDSCRAPER_AVAILABLE:
        try:
            session = cloudscraper.create_scraper()
        except Exception:
            session = requests.Session()
    else:
        session = requests.Session()

    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=16, pool_maxsize=16)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(DEFAULT_HEADERS)

    if cookie_file:
        ck_path = Path(cookie_file).resolve()
        if ck_path.is_file():
            try:
                jar = http.cookiejar.MozillaCookieJar(str(ck_path))
                jar.load(ignore_discard=True, ignore_expires=True)
                session.cookies.update(jar)
            except Exception:
                pass

    return session


def is_allowed_by_robots(url: str, user_agent: str = "*") -> bool:
    """Check if URL fetching is permitted by the site's robots.txt."""
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return True
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = urllib.robotparser.RobotFileParser(robots_url)
        rp.read()
        return rp.can_fetch(user_agent, url)
    except Exception:
        return True


def extract_images_from_html(html_text: str, base_url: str) -> List[str]:
    """Parse HTML and extract unique image URLs in sequential DOM occurrence order."""
    soup = BeautifulSoup(html_text, "html.parser")
    found_urls: List[str] = []
    seen: Set[str] = set()

    def _consider(candidate: str | None):
        if not candidate:
            return
        candidate = candidate.strip()
        if candidate.startswith("data:") or candidate.startswith("javascript:"):
            return
        full_url = urljoin(base_url, candidate)
        parsed_path = urlparse(full_url).path.lower()
        if any(parsed_path.endswith(ext) for ext in IMAGE_EXTENSIONS):
            if full_url not in seen:
                seen.add(full_url)
                found_urls.append(full_url)

    # 1. <img> tags: src, data-src, data-lazy, data-original, data-url, srcset
    for img in soup.find_all("img"):
        for attr in ["data-src", "data-lazy-src", "data-lazy", "data-original", "data-url", "data-srcset", "src"]:
            val = img.get(attr)
            if val:
                if attr.endswith("srcset"):
                    tokens = val.split(",")
                    if tokens:
                        first_token = tokens[-1].strip().split(" ")[0]
                        _consider(first_token)
                else:
                    _consider(val)

    # 2. <a> tags with direct image links
    for a in soup.find_all("a", href=True):
        href = a.get("href")
        _consider(href)

    # 3. <picture> <source> tags
    for source in soup.find_all("source"):
        for attr in ["srcset", "src", "data-srcset"]:
            val = source.get(attr)
            if val:
                _consider(val.split(",")[0].strip().split(" ")[0])

    # 4. CSS inline background-image: url(...)
    for tag in soup.find_all(style=True):
        style_val = tag.get("style", "")
        for match in re.findall(r'url\(["\']?([^"\')\s]+)["\']?\)', style_val):
            _consider(match)

    return found_urls


def get_html_title(html_text: str, fallback: str = "Comic_Chapter") -> str:
    """Extract and sanitize page <title> for folder naming."""
    try:
        soup = BeautifulSoup(html_text, "html.parser")
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
            title = re.sub(r"\s*[-|–]\s*(Read Online|Free Comics|Manga|Chapter).*$", "", title, flags=re.IGNORECASE)
            return safe_filename(title)
    except Exception:
        pass
    return safe_filename(fallback)


def download_single_image(
    session: requests.Session,
    url: str,
    target_path: Path,
    headers: Optional[dict] = None,
    timeout: int = 25,
    rotate_ua: bool = True,
) -> bool:
    """Download a single image file with atomic write."""
    if target_path.exists() and target_path.stat().st_size > 0:
        return True

    part_path = target_path.with_suffix(target_path.suffix + ".part")
    req_headers = dict(DEFAULT_HEADERS)
    if rotate_ua:
        req_headers["User-Agent"] = random.choice(USER_AGENTS)
    if headers:
        req_headers.update(headers)

    try:
        with session.get(url, headers=req_headers, stream=True, timeout=timeout) as resp:
            if resp.status_code != 200:
                return False

            part_path.parent.mkdir(parents=True, exist_ok=True)
            with open(part_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        f.write(chunk)

            if part_path.exists() and part_path.stat().st_size > 0:
                os.replace(part_path, target_path)
                return True
    except Exception:
        if part_path.exists():
            try:
                part_path.unlink()
            except Exception:
                pass
        return False
    return False


def scrape_and_download_comic(
    source: Union[str, Path, List[str]],
    output_base_dir: Optional[Union[str, Path]] = None,
    max_workers: int = 6,
    auto_format: Optional[str] = None,  # "pdf", "cbz", or None
    cookie_file: Optional[Union[str, Path]] = None,
    respect_robots: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Path:
    """
    Scrape comic/image gallery from a local HTML file, image directory, or live web URL.
    Optionally bundles downloaded images into PDF or CBZ.
    """
    if not output_base_dir:
        output_base_dir = Path(get_download_dir()) / "Comics"
    else:
        output_base_dir = Path(output_base_dir)

    output_base_dir.mkdir(parents=True, exist_ok=True)

    # 1. Check if source is a local folder of images
    if isinstance(source, (str, Path)) and os.path.isdir(str(source)):
        folder_path = Path(source).resolve()
        folder_title = folder_path.name
        chapter_dir = output_base_dir / folder_title
        chapter_dir.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            progress_callback(10, f"Copying images from local folder: {folder_path.name}...")

        import shutil
        img_files = [f for f in folder_path.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS]
        for f in img_files:
            dst = chapter_dir / f.name
            if not dst.exists():
                shutil.copy2(f, dst)

        if auto_format:
            fmt = auto_format.lower().lstrip(".")
            if fmt == "cbz":
                cbz_path = output_base_dir / f"{folder_title}.cbz"
                images_to_cbz(chapter_dir, cbz_path)
                return cbz_path
            elif fmt == "pdf":
                pdf_path = output_base_dir / f"{folder_title}.pdf"
                images_to_pdf(chapter_dir, pdf_path)
                return pdf_path

        return chapter_dir

    # 2. Build resilient session with Cloudflare bypass & cookies
    session = build_resilient_session(cookie_file=cookie_file)

    # Normalize source string
    src_str = str(source).strip()
    is_local_file = os.path.isfile(src_str) or src_str.startswith("file://")

    if is_local_file:
        file_path = src_str.replace("file://", "") if src_str.startswith("file://") else src_str
        file_path = Path(file_path).resolve()
        if not file_path.is_file():
            raise FileNotFoundError(f"Local HTML file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            html_text = f.read()

        base_url = f"file://{file_path}"
        folder_title = get_html_title(html_text, fallback=file_path.stem)
    else:
        # Live Web URL
        if respect_robots and not is_allowed_by_robots(src_str):
            raise PermissionError(f"robots.txt disallows scraping: {src_str}")

        if progress_callback:
            progress_callback(5, f"Fetching page: {src_str}...")

        resp = session.get(src_str, timeout=20)
        resp.raise_for_status()
        html_text = resp.text
        base_url = src_str
        parsed = urlparse(src_str)
        fallback_name = Path(parsed.path).stem or "Comic_Download"
        folder_title = get_html_title(html_text, fallback=fallback_name)

    # Extract image links
    image_urls = extract_images_from_html(html_text, base_url)
    if not image_urls:
        raise ValueError(f"No downloadable images discovered in: {source}")

    chapter_dir = output_base_dir / folder_title
    chapter_dir.mkdir(parents=True, exist_ok=True)

    total_images = len(image_urls)
    if progress_callback:
        progress_callback(10, f"Found {total_images} image(s). Starting download...")

    # Download images concurrently
    downloaded_count = 0
    futures = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for idx, img_url in enumerate(image_urls, start=1):
            parsed_path = urlparse(img_url).path
            ext = Path(parsed_path).suffix.lower()
            if ext not in IMAGE_EXTENSIONS:
                ext = ".jpg"
            img_filename = f"{idx:04d}{ext}"
            img_target = chapter_dir / img_filename

            custom_headers = {"Referer": base_url} if not is_local_file else None
            fut = executor.submit(download_single_image, session, img_url, img_target, custom_headers)
            futures[fut] = (idx, img_url)

        for fut in as_completed(futures):
            idx, url = futures[fut]
            try:
                ok = fut.result()
                if ok:
                    downloaded_count += 1
            except Exception:
                pass

            if progress_callback:
                pct = int(10 + (downloaded_count / total_images) * 80)
                progress_callback(pct, f"Downloaded {downloaded_count}/{total_images} images")

    # Optional PDF/CBZ bundling
    if auto_format:
        fmt = auto_format.lower().lstrip(".")
        if progress_callback:
            progress_callback(92, f"Bundling images into {fmt.upper()}...")

        if fmt == "cbz":
            cbz_path = output_base_dir / f"{folder_title}.cbz"
            images_to_cbz(chapter_dir, cbz_path)
            if progress_callback:
                progress_callback(100, f"Complete! Saved CBZ: {cbz_path.name}")
            return cbz_path
        elif fmt == "pdf":
            pdf_path = output_base_dir / f"{folder_title}.pdf"
            images_to_pdf(chapter_dir, pdf_path)
            if progress_callback:
                progress_callback(100, f"Complete! Saved PDF: {pdf_path.name}")
            return pdf_path

    if progress_callback:
        progress_callback(100, f"Downloaded {downloaded_count} images to: {chapter_dir.name}")

    return chapter_dir
