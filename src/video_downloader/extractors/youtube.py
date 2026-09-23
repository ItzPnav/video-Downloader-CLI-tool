from site_extractor import (
    extract_info,
    download,
)


def can_handle(route):

    return route.platform == "youtube"


def inspect(route):

    return extract_info(
        route.url
    )


def download_video(
    route,
    quality=None
):

    return download(
        route.url,
        quality
    )
