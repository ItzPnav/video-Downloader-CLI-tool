from dataclasses import dataclass
from typing import Callable


@dataclass
class Route:
    name: str
    platform: str
    media_type: str
    matcher: Callable
    extractor: Callable | None = None


class RouteRegistry:

    def __init__(self):
        self.routes = []

    def register(self, route):
        self.routes.append(route)

    def match(self, url):

        for route in self.routes:

            try:

                if route.matcher(url):
                    return route

            except Exception:
                continue

        return None

    def list_routes(self):
        return list(self.routes)
