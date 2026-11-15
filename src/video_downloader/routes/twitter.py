from .helpers import (
    host_matches,
    path,
)

DOMAINS = {
    "twitter.com",
    "x.com",
    "t.co",
    "fxtwitter.com",
    "vxtwitter.com",
    "fixupx.com",
}


def matches(url):

    return host_matches(
        url,
        DOMAINS
    )


def media_type(url):

    p = path(url)

    if "/i/spaces/" in p:
        return "spaces"

    if "/i/broadcasts/" in p:
        return "live"

    return "video"
