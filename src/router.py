from dataclasses import dataclass
from urllib.parse import urlparse

from routes import RouteRegistry

from routes import (
    youtube,
    tnaflix,
    vimeo,
    dailymotion,
    generic,
)


@dataclass
class ResolvedRoute:

    name: str
    platform: str
    media_type: str
    url: str


registry = RouteRegistry()


def register_routes():

    registry.routes.clear()

    registry.register(
        RouteRegistryRoute(
            "YouTube",
            "youtube",
            youtube.matches,
            youtube.media_type,
        )
    )

    registry.register(
        RouteRegistryRoute(
            "TNAFlix",
            "tnaflix",
            tnaflix.matches,
            tnaflix.media_type,
        )
    )

    registry.register(
        RouteRegistryRoute(
            "Vimeo",
            "vimeo",
            vimeo.matches,
            vimeo.media_type,
        )
    )

    registry.register(
        RouteRegistryRoute(
            "Dailymotion",
            "dailymotion",
            dailymotion.matches,
            dailymotion.media_type,
        )
    )

    # Generic must ALWAYS be last.
    registry.register(
        RouteRegistryRoute(
            "Generic",
            "generic",
            generic.matches,
            generic.media_type,
        )
    )


class RouteRegistryRoute:

    def __init__(
        self,
        name,
        platform,
        matcher,
        type_resolver,
    ):

        self.name = name
        self.platform = platform
        self.matcher = matcher
        self.type_resolver = type_resolver


register_routes()


def identify(url):

    for route in registry.routes:

        if route.matcher(url):

            return ResolvedRoute(
                name=route.name,
                platform=route.platform,
                media_type=route.type_resolver(url),
                url=url,
            )

    return ResolvedRoute(
        name="Generic",
        platform="generic",
        media_type="video",
        url=url,
    )


def describe(route):

    return (
        f"{route.name}"
        f" / "
        f"{route.media_type}"
    )


def available_routes():

    return [
        {
            "name": route.name,
            "platform": route.platform,
        }
        for route in registry.routes
    ]
