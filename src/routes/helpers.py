from urllib.parse import urlparse


def hostname(url):

    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return ""

    host = host.lower()

    if host.startswith("www."):
        host = host[4:]

    return host


def host_matches(url, domains):

    host = hostname(url)

    return any(
        host == domain
        or host.endswith("." + domain)
        for domain in domains
    )


def path(url):

    try:
        return (
            urlparse(url)
            .path
            .lower()
        )
    except Exception:
        return ""
