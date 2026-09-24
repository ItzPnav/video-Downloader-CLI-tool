# urlVideoDownloader_combo.py
import os
import time
import math
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Optional libs
try:
    import cloudscraper
except Exception:
    cloudscraper = None

try:
    from yt_dlp import YoutubeDL
except Exception:
    YoutubeDL = None

# Optional progress bar
try:
    from tqdm import tqdm as Tqdm
except Exception:
    Tqdm = None

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

VIDEO_EXTS = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".ts", ".m4v")

# ---------- Helpers ----------
def session_with_retries(total_retries=5, backoff=0.5):
    s = requests.Session()
    retries = Retry(total=total_retries, backoff_factor=backoff,
                    status_forcelist=(429, 500, 502, 503, 504),
                    allowed_methods=frozenset(['GET','HEAD']))
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def sanitize_filename(name):
    return "".join(c for c in name if c.isalnum() or c in " .-_()[]").strip()


def derive_name_and_dest(url, headers, download_folder):
    """Return (fname, dest, total_bytes) inferred from headers/url."""
    fname = None
    cd = headers.get("content-disposition") or headers.get("Content-Disposition")
    if cd and "filename=" in cd:
        fname = cd.split("filename=")[-1].strip('"; ')
    if not fname:
        fname = os.path.basename(urlparse(url).path) or "video"

    fname = sanitize_filename(fname)

    if not os.path.splitext(fname)[1]:
        ext = headers.get("content-type", "").split("/")[-1]
        if ext:
            fname += f".{ext}"

    dest = os.path.join(download_folder, fname)
    total = headers.get("Content-Length")
    return fname, dest, total

def is_video_content_type(ct):
    if not ct:
        return False
    return ct.startswith("video/") or any(x in ct for x in ("mp4","webm","mpeg","x-msvideo"))

# ---------- Finding links ----------
def find_video_links_from_html(page_url, html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    links = set()

    # video + source tags
    for tag in soup.find_all(["video", "source"]):
        src = tag.get("src") or tag.get("data-src")
        if src:
            links.add(urljoin(page_url, src))

    # anchor tags with video ext
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if any(href.lower().split("?")[0].endswith(ext) for ext in VIDEO_EXTS):
            links.add(urljoin(page_url, href))

    # inline JS hints (very naive)
    text = soup.get_text()
    for ext in VIDEO_EXTS:
        if ext in text:
            parts = text.split()
            for p in parts:
                if ext in p and "http" in p:
                    links.add(p.strip('",\'()[];'))

    return list(links)

# ---------- Direct download ----------
def download_stream(session_getter, url, dest_folder, chunk_size=1024*32, timeout=(10, 60)):
    try:
        sget = session_getter.get
        with sget(url, stream=True, timeout=timeout, allow_redirects=True) as resp:
            resp.raise_for_status()

            fname = None
            cd = resp.headers.get("content-disposition")
            if cd and "filename=" in cd:
                fname = cd.split("filename=")[-1].strip('"; ')
            if not fname:
                fname = os.path.basename(urlparse(resp.url).path) or "video"

            fname = sanitize_filename(fname)

            if not os.path.splitext(fname)[1]:
                ext = resp.headers.get("content-type", "").split("/")[-1]
                fname += f".{ext}"

            dest = os.path.join(dest_folder, fname)
            total = resp.headers.get("Content-Length")
            # If the exact file already exists, skip downloading
            if total and total.isdigit() and os.path.exists(dest):
                if os.path.getsize(dest) == int(total):
                    print(f"   ℹ Skipping {fname}: already downloaded ({dest}).")
                    return True
            if total:
                print(f"⏬ Downloading {fname} ({math.ceil(int(total)/1024)} KB)...")
            else:
                print(f"⏬ Downloading {fname} (size unknown)...")

            with open(dest, "wb") as f:
                        part_path = dest + ".part"
                        try:
                                    with open(part_path, "wb") as pf:
                                        pbar = None
                                        total_bytes = None
                                        if Tqdm is not None:
                                            try:
                                                total_bytes = int(resp.headers.get("Content-Length", 0)) or None
                                                pbar = Tqdm(total=total_bytes, unit='B', unit_scale=True, unit_divisor=1024, desc=fname)
                                            except Exception:
                                                pbar = None

                                        try:
                                            for chunk in resp.iter_content(chunk_size=chunk_size):
                                                if chunk:
                                                    pf.write(chunk)
                                                    if pbar is not None:
                                                        pbar.update(len(chunk))
                                        finally:
                                            if pbar is not None:
                                                pbar.close()

                                    # move temp file to final destination
                                    os.replace(part_path, dest)

                        except KeyboardInterrupt:
                            # User cancelled the download; remove partial file if exists
                            try:
                                if os.path.exists(part_path):
                                    os.remove(part_path)
                            except Exception:
                                pass
                            print("   ⛔ Download cancelled by user (KeyboardInterrupt).")
                            return False
                        except Exception as e:
                            # cleanup partial file on other errors
                            try:
                                if os.path.exists(part_path):
                                    os.remove(part_path)
                            except Exception:
                                pass
                            raise

            print(f"✅ Saved {dest}")
            return True

    except Exception as e:
        print(f"   ❌ download_stream error for {url} -> {e}")
        return False

def try_direct_downloads(page_url, download_folder):
    s = session_with_retries()
    s.headers.update(DEFAULT_HEADERS)

    try:
        print("🔍 Fetching page with requests...")
        r = s.get(page_url, timeout=(10,20))
        r.raise_for_status()
    except Exception as e:
        print(f"   ⚠ requests failed to fetch page: {e}")
        r = None

    links = []
    if r is not None:
        links = find_video_links_from_html(page_url, r.text)

    if not links:
        print("   ⚠ No direct links found with basic parsing.")
    else:
        print(f"   ℹ Found {len(links)} candidate file URLs.")

    os.makedirs(download_folder, exist_ok=True)

    for link in links:
        print("→ candidate:", link)
        try:
            h = s.head(link, allow_redirects=True, timeout=(8,15))

            # avoid downloading the same final file multiple times
            final_url = h.url
            fname, dest, total = derive_name_and_dest(final_url, h.headers, download_folder)
            # skip if file already exists and matches size
            if total and total.isdigit() and os.path.exists(dest):
                if os.path.getsize(dest) == int(total):
                    print(f"   ℹ Skipping {fname}: already downloaded ({dest}).")
                    continue

            content_type = h.headers.get("Content-Type", "")
            if is_video_content_type(content_type) or any(link.endswith(ext) for ext in VIDEO_EXTS):
                # Try parallel range download if server supports it
                accept_ranges = h.headers.get("Accept-Ranges", "").lower()
                total = h.headers.get("Content-Length")
                if accept_ranges and "bytes" in accept_ranges and total and total.isdigit():
                    try:
                        if try_parallel_download(s, link, download_folder):
                            return True
                    except Exception as e:
                        print(f"   ⚠ parallel download failed: {e}")

                # Fallback to single-stream download
                if download_stream(s, link, download_folder):
                    return True

            g = s.get(link, stream=True, timeout=(8,20))
            ct = g.headers.get("Content-Type", "")
            if is_video_content_type(ct):
                # check if already exists using final URL/headers
                fname2, dest2, total2 = derive_name_and_dest(g.url, g.headers, download_folder)
                if total2 and total2.isdigit() and os.path.exists(dest2):
                    if os.path.getsize(dest2) == int(total2):
                        print(f"   ℹ Skipping {fname2}: already downloaded ({dest2}).")
                        return True

                if download_stream(s, g.url, download_folder):
                    return True

        except Exception as e:
            print(f"   ⚠ request error for candidate {link}: {e}")

    return False


def try_parallel_download(session, url, download_folder, threads=4, chunk_size=1024*32):
    """Attempt to download the file using multiple byte-range requests in parallel.

    Returns True on success, False otherwise. This requires the server to support
    Accept-Ranges: bytes and provide a Content-Length header.
    """
    h = session.head(url, allow_redirects=True, timeout=(8,15))
    h.raise_for_status()

    total = h.headers.get("Content-Length")
    if not total or not total.isdigit():
        return False
    total = int(total)

    accept_ranges = h.headers.get("Accept-Ranges", "").lower()
    if "bytes" not in accept_ranges:
        return False

    fname = os.path.basename(urlparse(h.url).path) or "video"
    fname = sanitize_filename(fname)
    dest = os.path.join(download_folder, fname)
    os.makedirs(download_folder, exist_ok=True)

    # If the exact file already exists, skip parallel download
    if os.path.exists(dest) and os.path.getsize(dest) == total:
        print(f"   ℹ Skipping parallel: already downloaded ({dest}).")
        return True

    part_paths = []
    part_size = max(1, total // threads)
    ranges = []
    for i in range(threads):
        start = i * part_size
        end = (start + part_size - 1) if i < threads - 1 else total - 1
        ranges.append((start, end))

    lock = threading.Lock()
    pbar = None
    if Tqdm is not None:
        try:
            pbar = Tqdm(total=total, unit='B', unit_scale=True, unit_divisor=1024, desc=fname)
        except Exception:
            pbar = None

    def _download_range(idx, start, end):
        part_path = f"{dest}.part{idx}"
        headers = {"Range": f"bytes={start}-{end}"}
        try:
            with session.get(url, headers=headers, stream=True, timeout=(8,60), allow_redirects=True) as r:
                r.raise_for_status()
                with open(part_path, "wb") as pf:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if chunk:
                            pf.write(chunk)
                            if pbar is not None:
                                with lock:
                                    pbar.update(len(chunk))
            return part_path
        except Exception as e:
            # cleanup on error
            try:
                if os.path.exists(part_path):
                    os.remove(part_path)
            except Exception:
                pass
            raise e

    # submit workers
    parts = []
    try:
        with ThreadPoolExecutor(max_workers=threads) as ex:
            futures = {ex.submit(_download_range, i, s, e): i for i, (s, e) in enumerate(ranges)}
            for fut in as_completed(futures):
                idx = futures[fut]
                part = fut.result()
                parts.append((idx, part))

        # close progress bar
        if pbar is not None:
            pbar.close()

        # sort parts and concatenate
        parts.sort()
        with open(dest + ".partall", "wb") as out:
            for idx, part in parts:
                with open(part, "rb") as pf:
                    out.write(pf.read())

        os.replace(dest + ".partall", dest)

        # remove part files
        for idx, part in parts:
            try:
                os.remove(part)
            except Exception:
                pass

        print(f"✅ Parallel saved {dest}")
        return True

    except KeyboardInterrupt:
        print("   ⛔ Parallel download cancelled by user.")
        for _, part in parts:
            try:
                if os.path.exists(part):
                    os.remove(part)
            except Exception:
                pass
        if pbar is not None:
            pbar.close()
        return False
    except Exception as e:
        if pbar is not None:
            pbar.close()
        # cleanup any parts
        for _, part in parts:
            try:
                if os.path.exists(part):
                    os.remove(part)
            except Exception:
                pass
        raise

# ---------- cloudscraper fallback ----------
def try_cloudscraper_and_direct(page_url, download_folder):
    if cloudscraper is None:
        print("   ⚠ cloudscraper not installed or import failed.")
        return False

    try:
        print("🔍 Trying cloudscraper (Cloudflare bypass)...")
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(page_url, timeout=20)
        resp.raise_for_status()

        links = find_video_links_from_html(page_url, resp.text)
        print(f"   ℹ cloudscraper found {len(links)} candidate(s).")

        for link in links:
            print("→ candidate (cloudscraper):", link)
            try:
                g = scraper.get(link, stream=True, timeout=(10,60))
                ct = g.headers.get("Content-Type", "")
                if is_video_content_type(ct):
                    if download_stream(scraper, link, download_folder):
                        return True
            except Exception as e:
                print(f"   ⚠ cloudscraper error: {e}")

    except Exception as e:
        print(f"   ⚠ cloudscraper failed: {e}")

    return False

# ---------- yt-dlp fallback (MAXIMUM QUALITY) ----------
def try_yt_dlp(url, download_folder, verbose=True):
    if YoutubeDL is None:
        print("   ⚠ yt-dlp not installed or import failed.")
        return False

    ydl_opts = {
        "outtmpl": os.path.join(download_folder, "%(title)s.%(ext)s"),

        # ⭐ Maximum resolution video + best audio
        "format": "bestvideo+bestaudio/best",

        # ⭐ Merge into MP4
        "merge_output_format": "mp4",

        "noplaylist": False,
        "quiet": not verbose,
        "no_warnings": True,
        "retries": 10,
    }

    os.makedirs(download_folder, exist_ok=True)

    try:
        print("🔧 Falling back to yt-dlp (highest quality)...")
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        print("✅ yt-dlp finished (max quality downloaded).")
        return True

    except Exception as e:
        print(f"   ❌ yt-dlp failed: {e}")
        return False


    # ---------- Twitter Video Downloader Function ----------
DEFAULT_DOWNLOAD_FOLDER = r"C:\pnav\extra\others\video"


def download_twitter_video(url, download_folder=DEFAULT_DOWNLOAD_FOLDER, verbose=True):
    from yt_dlp import YoutubeDL
    COOKIE_FILE = "cookies.txt"

    print("\n==============================")
    print(" TWITTER/X Video Extractor")
    print("==============================")

    # Build yt-dlp options
    ydl_opts = {
        "outtmpl": os.path.join(download_folder, "%(title)s.%(ext)s"),
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "retries": 10,
        "quiet": not verbose,
        "no_warnings": not verbose,
    }

    # Add cookies if exists
    if os.path.exists(COOKIE_FILE):
        print(f"[INFO] Using cookies from {COOKIE_FILE}")
        ydl_opts["cookiefile"] = COOKIE_FILE
    else:
        print("[INFO] No cookies.txt found. Only PUBLIC tweets will work.")

    os.makedirs(download_folder, exist_ok=True)

    try:
        print("[INFO] Fetching available video qualities...")
        # Preview formats
        list_opts = ydl_opts.copy()
        list_opts["skip_download"] = True
        list_opts["listformats"] = True

        with YoutubeDL(list_opts) as ydl:
            ydl.extract_info(url, download=False)

        print("\n[INFO] Downloading BEST quality available...")
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        print("🔥 Successfully downloaded from Twitter/X.\n")
        return True

    except Exception as e:
        print(f"❌ Twitter video extraction failed: {e}")
        return False


# ---------- Main ----------
def download_from_url(url, download_folder=DEFAULT_DOWNLOAD_FOLDER):
    print(f"Start -> {url}")
    print(f"Saving to -> {download_folder}")

    if "twitter.com" in url or "x.com" in url:
        print("Trying Twitter/X downloader...")
        ok = download_twitter_video(url, download_folder)
        if ok:
            return


    if try_direct_downloads(url, download_folder):
        return

    if try_cloudscraper_and_direct(url, download_folder):
        return

    if try_yt_dlp(url, download_folder):
        return

    print("✖ All methods failed. Site may block downloads or require login.")

if __name__ == "__main__":
    src = input("Enter a website URL: ").strip()
    download_from_url(src)
