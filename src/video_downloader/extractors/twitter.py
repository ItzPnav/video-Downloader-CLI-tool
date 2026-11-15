"""
X / Twitter Video Computation & Extraction Engine.

Ported from twitter-dl (tdl/core.py) computation flow:
1. URL parsing and shortlink resolution for x.com, twitter.com, fxtwitter, vxtwitter, fixupx, t.co.
2. Three-tier extraction cascade:
   - X public syndication embed API (cdn.syndication.twimg.com/tweet-result) with base-36 token math
   - FxTwitter JSON mirror API (api.fxtwitter.com) for region/age-gate resilience
   - yt-dlp direct MP4 format filter
3. Variant quality selection ('best', 'worst', or max height <= N like 720p).
4. Media host security guard (*.twimg.com).
"""
from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

import requests

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    from ..candidate import Candidate
except (ImportError, ValueError):
    from video_downloader.candidate import Candidate

TWEET_RE = re.compile(
    r"^https?://(?:www\.|mobile\.)?(?:twitter|x|fxtwitter|vxtwitter|fixupx)\.com/"
    r"(?:i/web/|(\w+)/)status/(\d+)(?:/video/(\d+))?",
    re.IGNORECASE,
)
SHORTLINK_RE = re.compile(r"^https?://t\.co/[A-Za-z0-9]+", re.IGNORECASE)
MEDIA_HOST_SUFFIX = "twimg.com"
CHUNK_SIZE = 64 * 1024

ProgressFn = Callable[[int, Optional[int]], None]  # (bytes_done, total_or_None)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_B36 = "0123456789abcdefghijklmnopqrstuvwxyz"
_RES_RE = re.compile(r"/(\d+)x(\d+)/")


# --------------------------------------------------------------------------- #
# Errors. Each carries a stable `code` so callers can branch without parsing text.
# --------------------------------------------------------------------------- #
class TdlError(Exception):
    code = "error"


class InvalidURLError(TdlError):
    code = "invalid_url"


class FetchError(TdlError):
    code = "fetch_failed"


class NoVideoError(TdlError):
    code = "no_video"


class DownloadError(TdlError):
    code = "download_failed"


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class TweetRef:
    user: str
    tweet_id: str
    video_index: Optional[int] = None

    @property
    def canonical(self) -> str:
        return f"https://x.com/{self.user}/status/{self.tweet_id}"


@dataclass(frozen=True)
class Variant:
    height: int
    width: int
    bitrate_kbps: int
    url: str
    size_bytes: Optional[int] = None


@dataclass
class Video:
    index: int
    duration_s: Optional[float]
    thumbnail: Optional[str]
    variants: List[Variant] = field(default_factory=list)

    def pick(self, quality: Union[str, int] = "best") -> Variant:
        """'best' | 'worst' | N (highest variant with height <= N, else the smallest)."""
        if not self.variants:
            raise NoVideoError("No downloadable MP4 variants for this video.")
        ordered = sorted(self.variants, key=lambda v: (v.height, v.bitrate_kbps))
        q = str(quality if quality is not None else "best").strip().lower().rstrip("p")
        if not q or q == "best":
            return ordered[-1]
        if q == "worst":
            return ordered[0]
        if q.isdigit():
            limit = int(q)
            fitting = [v for v in ordered if v.height <= limit]
            return fitting[-1] if fitting else ordered[0]
        raise ValueError(
            f"Unknown quality {quality!r}; use best, worst, or a number like 720."
        )


@dataclass
class TweetInfo:
    ref: TweetRef
    author: str
    text: str
    videos: List[Video] = field(default_factory=list)
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["url"] = self.ref.canonical
        return data


# --------------------------------------------------------------------------- #
# URL handling
# --------------------------------------------------------------------------- #
def is_twitter_url(url: str) -> bool:
    cleaned = (url or "").strip()
    return bool(TWEET_RE.match(cleaned) or SHORTLINK_RE.match(cleaned))


def resolve_shortlink(url: str, timeout: float = 10.0) -> str:
    cleaned = (url or "").strip()
    if not SHORTLINK_RE.match(cleaned):
        return cleaned
    try:
        resp = requests.head(
            cleaned,
            headers={"User-Agent": _UA},
            allow_redirects=True,
            timeout=timeout,
        )
        if resp.url:
            return resp.url
    except Exception:
        pass
    return cleaned


def parse_url(url: str) -> TweetRef:
    cleaned = resolve_shortlink((url or "").strip())
    match = TWEET_RE.match(cleaned)
    if not match:
        raise InvalidURLError(
            "Not a post link. Expected https://x.com/<user>/status/<id>."
        )
    user = match.group(1) or "i"
    tweet_id = match.group(2)
    vid_idx = int(match.group(3)) if match.group(3) else None
    return TweetRef(user=user, tweet_id=tweet_id, video_index=vid_idx)


def ensure_media_url(url: str) -> None:
    """Refuse anything that is not X's media CDN, so we are never an open proxy."""
    host = (urlparse(url).hostname or "").lower()
    ok = host == MEDIA_HOST_SUFFIX or host.endswith("." + MEDIA_HOST_SUFFIX)
    if not ok:
        raise DownloadError(f"Refusing to fetch from {host or 'unknown host'}.")


# --------------------------------------------------------------------------- #
# Source 1: yt-dlp direct MP4 format extraction
# --------------------------------------------------------------------------- #
def _variants_from_formats(formats: List[Dict[str, Any]]) -> List[Variant]:
    seen = set()
    variants: List[Variant] = []
    for f in formats:
        direct = f.get("protocol") in ("https", "http")
        has_video = f.get("vcodec") != "none"
        is_mp4 = f.get("ext") == "mp4"
        url = f.get("url")
        if not (direct and has_video and is_mp4 and url and url not in seen):
            continue
        seen.add(url)
        variants.append(
            Variant(
                height=int(f.get("height") or 0),
                width=int(f.get("width") or 0),
                bitrate_kbps=int(f.get("tbr") or 0),
                url=url,
                size_bytes=f.get("filesize") or f.get("filesize_approx"),
            )
        )
    variants.sort(key=lambda v: (v.height, v.bitrate_kbps), reverse=True)
    return variants


def _from_ytdlp(ref: TweetRef, ydl_opts: Optional[Dict[str, Any]] = None) -> TweetInfo:
    if yt_dlp is None:
        raise FetchError("yt-dlp: library not installed")

    opts: Dict[str, Any] = {"quiet": True, "no_warnings": True, "skip_download": True}
    opts.update(ydl_opts or {})

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            data = ydl.extract_info(ref.canonical, download=False)
    except Exception as exc:
        reason = str(exc).replace("ERROR: ", "").strip()
        raise FetchError(f"yt-dlp: {reason}") from exc

    entries = data.get("entries") or [data]
    videos: List[Video] = []
    for i, entry in enumerate(entries):
        variants = _variants_from_formats(entry.get("formats") or [])
        videos.append(
            Video(
                index=i,
                duration_s=entry.get("duration"),
                thumbnail=entry.get("thumbnail"),
                variants=variants,
            )
        )

    if not any(v.variants for v in videos):
        raise NoVideoError("yt-dlp: no direct MP4 variants.")

    first = entries[0]
    return TweetInfo(
        ref=ref,
        author=first.get("uploader") or first.get("channel") or ref.user,
        text=(first.get("description") or first.get("title") or "").strip(),
        videos=videos,
        source="ytdlp",
    )


# --------------------------------------------------------------------------- #
# Source 2: X's public embed endpoint (cdn.syndication.twimg.com)
# --------------------------------------------------------------------------- #
def _syndication_token(tweet_id: str) -> str:
    """Port of the token the embed widget sends: (id / 1e15 * pi) in base 36, zeros and dot removed."""
    n = int(tweet_id) / 1e15 * math.pi
    whole, frac = int(n), n - int(n)
    head = ""
    while whole:
        whole, d = divmod(whole, 36)
        head = _B36[d] + head
    tail = ""
    for _ in range(12):
        frac *= 36
        d = int(frac)
        tail += _B36[d]
        frac -= d
    return re.sub(r"(0+|\.)", "", (head or "0") + "." + tail)


def _variants_from_api(raw_variants: List[Dict[str, Any]]) -> List[Variant]:
    out: List[Variant] = []
    seen = set()
    for rv in raw_variants:
        url = rv.get("url") or rv.get("src") or ""
        is_mp4 = rv.get("content_type", rv.get("type")) == "video/mp4"
        if not is_mp4 or not url or url in seen:
            continue
        seen.add(url)
        m = _RES_RE.search(url)
        width, height = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
        out.append(
            Variant(
                height=height,
                width=width,
                bitrate_kbps=int(rv.get("bitrate") or 0) // 1000,
                url=url,
            )
        )
    out.sort(key=lambda v: (v.height, v.bitrate_kbps), reverse=True)
    return out


def _info_from_syndication(ref: TweetRef, data: Dict[str, Any]) -> TweetInfo:
    if data.get("__typename") == "TweetTombstone" or not data:
        raise FetchError("embed: post is unavailable (deleted, protected, or restricted).")

    # The post's own media first, then a quoted post, then the parent
    candidates = [data, data.get("quoted_tweet") or {}, data.get("parent") or {}]
    videos: List[Video] = []
    for source in candidates:
        for media in source.get("mediaDetails") or []:
            info = media.get("video_info")
            if media.get("type") not in ("video", "animated_gif") or not info:
                continue
            variants = _variants_from_api(info.get("variants") or [])
            if variants:
                videos.append(
                    Video(
                        index=len(videos),
                        duration_s=(info.get("duration_millis") or 0) / 1000 or None,
                        thumbnail=media.get("media_url_https"),
                        variants=variants,
                    )
                )
        if videos:
            break

    if not videos:
        raise NoVideoError("embed: response had no video (it may be restricted or sensitive).")

    user = data.get("user") or {}
    resolved_ref = ref
    if ref.user == "i" and user.get("screen_name"):
        resolved_ref = TweetRef(
            user=user["screen_name"],
            tweet_id=ref.tweet_id,
            video_index=ref.video_index,
        )

    return TweetInfo(
        ref=resolved_ref,
        author=user.get("name") or user.get("screen_name") or resolved_ref.user,
        text=(data.get("text") or "").strip(),
        videos=videos,
        source="embed",
    )


def _requests_proxies(ydl_opts: Optional[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    proxy = (ydl_opts or {}).get("proxy")
    if proxy:
        return {"http": proxy, "https": proxy}
    return None


def _from_syndication(ref: TweetRef, ydl_opts: Optional[Dict[str, Any]] = None) -> TweetInfo:
    params = {
        "id": ref.tweet_id,
        "lang": "en",
        "token": _syndication_token(ref.tweet_id),
    }
    try:
        resp = requests.get(
            "https://cdn.syndication.twimg.com/tweet-result",
            params=params,
            headers={"User-Agent": _UA},
            proxies=_requests_proxies(ydl_opts),
            timeout=15.0,
            allow_redirects=True,
        )
        if resp.status_code != 200:
            raise FetchError(f"embed: HTTP {resp.status_code}")
        data = resp.json()
    except FetchError:
        raise
    except Exception as exc:
        raise FetchError(f"embed: {exc}") from exc
    return _info_from_syndication(ref, data)


# --------------------------------------------------------------------------- #
# Source 3: fxtwitter mirror (api.fxtwitter.com)
# --------------------------------------------------------------------------- #
def _info_from_fxtwitter(ref: TweetRef, data: Dict[str, Any]) -> TweetInfo:
    tweet = data.get("tweet") or {}
    if not tweet:
        raise FetchError(f"fxtwitter: {data.get('message') or 'no tweet in response'}")

    videos: List[Video] = []
    for source in (tweet, tweet.get("quote") or {}):
        for v in (source.get("media") or {}).get("videos") or []:
            url = v.get("url") or ""
            if not url or ".m3u8" in url:
                continue
            variants = _variants_from_api(v.get("variants") or [])
            if not variants:
                variants = [
                    Variant(
                        height=int(v.get("height") or 0),
                        width=int(v.get("width") or 0),
                        bitrate_kbps=0,
                        url=url,
                    )
                ]
            videos.append(
                Video(
                    index=len(videos),
                    duration_s=v.get("duration"),
                    thumbnail=v.get("thumbnail_url"),
                    variants=variants,
                )
            )
        if videos:
            break

    if not videos:
        raise NoVideoError("fxtwitter: no video in response.")

    author = tweet.get("author") or {}
    resolved_ref = ref
    if ref.user == "i" and author.get("screen_name"):
        resolved_ref = TweetRef(
            user=author["screen_name"],
            tweet_id=ref.tweet_id,
            video_index=ref.video_index,
        )

    return TweetInfo(
        ref=resolved_ref,
        author=author.get("name") or resolved_ref.user,
        text=(tweet.get("text") or "").strip(),
        videos=videos,
        source="fxtwitter",
    )


def _from_fxtwitter(ref: TweetRef, ydl_opts: Optional[Dict[str, Any]] = None) -> TweetInfo:
    try:
        resp = requests.get(
            f"https://api.fxtwitter.com/{ref.user}/status/{ref.tweet_id}",
            headers={"User-Agent": _UA},
            proxies=_requests_proxies(ydl_opts),
            timeout=15.0,
            allow_redirects=True,
        )
        data = resp.json()
    except Exception as exc:
        raise FetchError(f"fxtwitter: {exc}") from exc
    return _info_from_fxtwitter(ref, data)


# --------------------------------------------------------------------------- #
# Public computation entry points
# --------------------------------------------------------------------------- #
_API_SOURCES: Tuple[Tuple[str, Callable], ...] = (
    ("embed", _from_syndication),
    ("fxtwitter", _from_fxtwitter),
)

_SOURCES: Tuple[Tuple[str, Callable], ...] = (
    ("ytdlp", _from_ytdlp),
    ("embed", _from_syndication),
    ("fxtwitter", _from_fxtwitter),
)


def fetch_info(
    url: str,
    ydl_opts: Optional[Dict[str, Any]] = None,
    sources: Optional[Tuple[Tuple[str, Callable], ...]] = None,
) -> TweetInfo:
    """Try each source in order; first one that finds a video wins."""
    ref = parse_url(url)
    failures: List[str] = []
    active_sources = sources if sources is not None else _SOURCES
    for _name, fn in active_sources:
        try:
            return fn(ref, ydl_opts)
        except TdlError as exc:
            failures.append(str(exc))

    raise NoVideoError(
        "No source could find a video in this post. " + " | ".join(failures)
    )


def default_filename(ref: TweetRef, video: Video, variant: Variant, multiple: bool) -> str:
    part = f"_{video.index + 1}" if multiple else ""
    height_tag = f"_{variant.height}p" if variant.height else ""
    return f"{ref.user}_{ref.tweet_id}{part}{height_tag}.mp4"


def download(
    variant: Variant,
    dest_dir: Union[str, Path] = ".",
    filename: str = "video.mp4",
    progress: Optional[ProgressFn] = None,
    overwrite: bool = False,
) -> Path:
    """Stream a variant to disk. Writes to <name>.part, then renames on success."""
    ensure_media_url(variant.url)

    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    final = dest / re.sub(r"[^\w.\-]", "_", filename)
    part = final.with_suffix(final.suffix + ".part")

    if final.exists() and not overwrite:
        return final

    done = 0
    try:
        with requests.get(
            variant.url,
            headers={"User-Agent": _UA},
            stream=True,
            allow_redirects=True,
            timeout=(15.0, 60.0),
        ) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length") or 0) or variant.size_bytes
            with open(part, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                    if not chunk:
                        continue
                    fh.write(chunk)
                    done += len(chunk)
                    if progress:
                        progress(done, total)
        part.replace(final)
    except Exception as exc:
        part.unlink(missing_ok=True)
        raise DownloadError(f"Download failed: {exc}") from exc

    return final


# --------------------------------------------------------------------------- #
# Tool-Kit CLI Candidate & Route Integration
# --------------------------------------------------------------------------- #
def extract_twitter_candidate(
    url: str,
    requested_quality: Optional[str] = None,
    include_ytdlp: bool = False,
) -> Optional[Candidate]:
    """
    Resolve an X/Twitter post URL into a scored Tool-Kit CLI Candidate.
    Uses fast HTTP APIs (Syndication + FxTwitter) first, optionally falling back to yt-dlp.
    """
    if not is_twitter_url(url):
        return None

    sources = (_API_SOURCES + (("ytdlp", _from_ytdlp),)) if include_ytdlp else _API_SOURCES
    try:
        info = fetch_info(url, sources=sources)
    except TdlError:
        return None

    valid_videos = [v for v in info.videos if v.variants]
    if not valid_videos:
        return None

    target_video = valid_videos[0]
    if info.ref.video_index is not None:
        matched = [v for v in valid_videos if v.index == info.ref.video_index - 1]
        if matched:
            target_video = matched[0]

    try:
        variant = target_video.pick(requested_quality or "best")
    except (ValueError, TdlError):
        variant = target_video.pick("best")

    try:
        ensure_media_url(variant.url)
    except DownloadError:
        return None

    multiple = len(info.videos) > 1
    fname = default_filename(info.ref, target_video, variant, multiple)
    title_stem = Path(fname).stem

    return Candidate(
        url=variant.url,
        source=f"twitter:{info.source}",
        mime_type="video/mp4",
        status=200,
        extension=".mp4",
        score=100,
        metadata={
            "title": title_stem,
            "author": info.author,
            "text": info.text,
            "user": info.ref.user,
            "tweet_id": info.ref.tweet_id,
            "height": variant.height,
            "width": variant.width,
            "bitrate_kbps": variant.bitrate_kbps,
            "duration_s": target_video.duration_s,
            "thumbnail": target_video.thumbnail,
            "original_url": info.ref.canonical,
            "engine": f"twitter:{info.source}",
            "variants_count": len(target_video.variants),
        },
    )


def can_handle(route) -> bool:
    return getattr(route, "platform", "") == "twitter"


def inspect(route) -> Optional[Dict[str, Any]]:
    try:
        return fetch_info(route.url).to_dict()
    except TdlError:
        return None


def download_video(route, quality: Optional[str] = None):
    candidate = extract_twitter_candidate(route.url, requested_quality=quality, include_ytdlp=True)
    if not candidate:
        return False
    try:
        from ..downloader import download as toolkit_download
    except (ImportError, ValueError):
        from video_downloader.downloader import download as toolkit_download
    return toolkit_download(
        candidate,
        filename=candidate.metadata.get("title", "video"),
        requested_quality=quality,
    )
