import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def main():

    if len(sys.argv) != 2:
        print('Usage: python src/browser_diag.py "URL"')
        return 1

    url = sys.argv[1]

    options = Options()

    options.binary_location = (
        "/data/data/com.termux/files/usr/bin/chromium-browser"
    )

    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,720")

    print()
    print("=" * 60)
    print("              CHROMIUM NETWORK DIAGNOSTIC")
    print("=" * 60)
    print()
    print("[+] Starting Chromium...")

    driver = webdriver.Chrome(
        options=options
    )

    try:

        driver.set_page_load_timeout(45)

        print("[+] Loading URL...")

        start = time.time()

        try:

            driver.get(url)

            elapsed = time.time() - start

            print(
                f"[✓] Page loaded in {elapsed:.1f}s"
            )

        except Exception as error:

            elapsed = time.time() - start

            print(
                f"[!] Page load exception after "
                f"{elapsed:.1f}s"
            )

            print(
                f"    {error}"
            )

        print()
        print("[+] Browser state")

        print(
            f"    Current URL : {driver.current_url}"
        )

        print(
            f"    Title       : {driver.title}"
        )

        html = driver.page_source

        print(
            f"    HTML size   : {len(html):,} bytes"
        )

        # ----------------------------------------------------
        # Video elements
        # ----------------------------------------------------

        videos = driver.find_elements(
            "tag name",
            "video"
        )

        print()
        print(
            f"[+] <video> elements: {len(videos)}"
        )

        for i, video in enumerate(
            videos[:10],
            1
        ):

            print(
                f"    [{i}]"
            )

            print(
                f"        src: "
                f"{video.get_attribute('src')}"
            )

            print(
                f"        currentSrc: "
                f"{driver.execute_script("
                    "return arguments[0].currentSrc",
                    video
                )}"
            )

        # ----------------------------------------------------
        # Source elements
        # ----------------------------------------------------

        sources = driver.find_elements(
            "tag name",
            "source"
        )

        print()
        print(
            f"[+] <source> elements: {len(sources)}"
        )

        for i, source in enumerate(
            sources[:20],
            1
        ):

            print(
                f"    [{i}] "
                f"{source.get_attribute('src')}"
            )

        # ----------------------------------------------------
        # Iframes
        # ----------------------------------------------------

        iframes = driver.find_elements(
            "tag name",
            "iframe"
        )

        print()
        print(
            f"[+] <iframe> elements: {len(iframes)}"
        )

        for i, iframe in enumerate(
            iframes[:20],
            1
        ):

            print(
                f"    [{i}] "
                f"{iframe.get_attribute('src')}"
            )

        # ----------------------------------------------------
        # Performance network entries
        # ----------------------------------------------------

        print()
        print(
            "[+] Browser network entries"
        )

        entries = driver.execute_script(
            "return performance.getEntriesByType('resource')"
        )

        media = []

        for entry in entries:

            name = entry.get(
                "name",
                ""
            )

            lower = name.lower()

            if any(
                x in lower
                for x in (
                    ".mp4",
                    ".webm",
                    ".m3u8",
                    ".m4v",
                    ".mpd",
                    ".ts",
                    "video",
                    "manifest"
                )
            ):

                media.append(name)

        if media:

            for item in media[:50]:

                print(
                    f"    ✓ {item}"
                )

        else:

            print(
                "    No obvious media resources."
            )

        # ----------------------------------------------------
        # Body text
        # ----------------------------------------------------

        text = driver.find_element(
            "tag name",
            "body"
        ).text

        print()
        print(
            f"[+] Visible text: "
            f"{len(text):,} characters"
        )

        print()

    finally:

        driver.quit()

        print(
            "[+] Chromium closed."
        )


if __name__ == "__main__":
    sys.exit(main())
