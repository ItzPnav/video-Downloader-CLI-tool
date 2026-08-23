from site_extractor import (
    extract_info,
    download,
)


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
