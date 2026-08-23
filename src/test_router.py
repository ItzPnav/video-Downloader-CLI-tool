import sys

from router import (
    identify,
    available_routes,
)


tests = [
    "https://youtube.com/watch?v=test",
    "https://youtube.com/shorts/test",
    "https://youtu.be/test",
    "https://www.tnaflix.com/video123",
    "https://vimeo.com/123456",
    "https://www.dailymotion.com/video/test",
    "https://example.com/video/test",
]


print()
print("=" * 60)
print("                 ROUTER TEST")
print("=" * 60)
print()

for url in tests:

    route = identify(url)

    print(
        f"{route.name:<15}"
        f"{route.media_type:<12}"
        f"{route.url}"
    )

print()
print("Available routes:")

for route in available_routes():

    print(
        f"  ✓ {route['name']}"
        f" ({route['platform']})"
    )

print()
