from .helpers import host_matches


DOMAINS = {
    "tnaflix.com",
}


def matches(url):

    return host_matches(
        url,
        DOMAINS
    )


def media_type(url):

    return "video"
