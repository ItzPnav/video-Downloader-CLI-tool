from dataclasses import dataclass, field
from urllib.parse import urlparse


VIDEO_EXTENSIONS = {
    ".mp4", ".webm", ".m4v", ".mov", ".ogv", ".ogg",
    ".mpeg", ".mpg", ".mpe", ".m2v", ".m2ts", ".mts",
    ".ts", ".3gp", ".3g2", ".flv", ".f4v", ".avi",
    ".wmv", ".asf", ".mkv", ".vob", ".divx", ".rm",
    ".rmvb"
}

STREAM_EXTENSIONS = {
    ".m3u8", ".mpd", ".ism", ".isml", ".m3u"
}


@dataclass
class Candidate:
    url: str
    source: str
    mime_type: str = ""
    status: int | None = None
    extension: str = ""
    score: int = 0
    metadata: dict = field(default_factory=dict)

    @property
    def is_stream(self):
        return self.extension.lower() in STREAM_EXTENSIONS

    @property
    def is_direct_video(self):
        return self.extension.lower() in VIDEO_EXTENSIONS

    @property
    def label(self):
        if self.is_stream:
            return "STREAM"
        if self.is_direct_video:
            return "VIDEO"
        return "UNKNOWN"


def detect_extension(url: str) -> str:
    try:
        path = urlparse(url).path.lower()

        for ext in VIDEO_EXTENSIONS | STREAM_EXTENSIONS:
            if path.endswith(ext):
                return ext

    except Exception:
        pass

    return ""


def score_candidate(candidate: Candidate) -> int:
    score = 0

    ext = candidate.extension.lower()
    mime = candidate.mime_type.lower()
    url = candidate.url.lower()

    if ext == ".m3u8":
        score += 100

    elif ext == ".mpd":
        score += 100

    elif ext == ".mp4":
        score += 95

    elif ext == ".webm":
        score += 90

    elif ext in VIDEO_EXTENSIONS:
        score += 70

    if mime.startswith("video/"):
        score += 50

    if "mpegurl" in mime:
        score += 50

    if "dash+xml" in mime:
        score += 50

    if "master" in url:
        score += 15

    if "playlist" in url:
        score += 10

    if "manifest" in url:
        score += 10

    if candidate.status == 200:
        score += 10

    candidate.score = score

    return score
