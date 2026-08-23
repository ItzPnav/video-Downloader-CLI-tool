from .helpers import (
    host_matches,
    path,
)

DOMAINS = {
    "youtube.com",
    "youtu.be",
}


def matches(url):

    return host_matches(
        url,
        DOMAINS
    )


def media_type(url):

    p = path(url)

    if p.startswith("/shorts/"):
        return "shorts"

    if p.startswith("/live/"):
        return "live"

    if p.startswith("/embed/"):
        return "embed"

    return "video"
