import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Base folder where all comics will be saved
base_folder_path = r"C:\pnav\extra\others\comic"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    )
}


def sanitize_filename(name):
    """
    Remove invalid Windows filename characters.
    """
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'_+', '_', name)
    return name.strip(" ._")


def download_image(url, folder):
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)

        if response.status_code != 200:
            print(f"Failed ({response.status_code}): {url}")
            return

        filename = os.path.basename(url.split("?")[0])
        filepath = os.path.join(folder, filename)

        if os.path.exists(filepath):
            print(f"Already exists: {filename}")
            return

        with open(filepath, "wb") as f:
            f.write(response.content)

        print(f"Downloaded: {filename}")

    except Exception as e:
        print(f"Error downloading {url}")
        print(e)


allLinks = ['https://www.freecomics.xxx/books/3931.html', 'https://www.freecomics.xxx/books/3932.html', 'https://www.freecomics.xxx/books/3933.html', 'https://www.freecomics.xxx/books/3934.html', 'https://www.freecomics.xxx/books/3935.html', 'https://www.freecomics.xxx/books/3936.html', 'https://www.freecomics.xxx/books/3937.html', 'https://www.freecomics.xxx/books/892.html', 'https://www.freecomics.xxx/books/893.html', 'https://www.freecomics.xxx/books/5959.html']


for l in allLinks:
    page_url = l

    if not page_url:
        print("Please enter a valid URL.")
        continue

    try:
        response = requests.get(page_url, headers=HEADERS, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Folder name
        if soup.title and soup.title.string:
            folder_name = sanitize_filename(soup.title.string)
        else:
            folder_name = "Downloaded_Comic"

        new_folder_path = os.path.join(base_folder_path, folder_name)
        os.makedirs(new_folder_path, exist_ok=True)

        print(f"\nFolder: {new_folder_path}")

        image_urls = set()

        # Images
        for img in soup.find_all("img"):
            for attr in ["data-src", "src"]:
                src = img.get(attr)
                if src:
                    full_url = urljoin(page_url, src)

                    if full_url.lower().endswith(
                        (".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg")
                    ):
                        image_urls.add(full_url)

        # Direct image links
        for a in soup.find_all("a"):
            href = a.get("href")
            if href:
                full_url = urljoin(page_url, href)

                if full_url.lower().endswith(
                    (".jpg", ".jpeg", ".png", ".webp")
                ):
                    image_urls.add(full_url)

        if not image_urls:
            print("No downloadable images found.")
        else:
            print(f"Found {len(image_urls)} image(s).\n")

            for img_url in sorted(image_urls):
                download_image(img_url, new_folder_path)

    except Exception as e:
        print(f"\nError processing the URL:")
        print(e)
