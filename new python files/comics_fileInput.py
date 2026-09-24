import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Path to your local HTML file
html_file_path = input("Enter html file path: ").strip()
with open(html_file_path, 'r', encoding='utf-8') as file:
    print("File opened successfully!")



# Base folder path where you want to create the title-named folder
base_folder_path = r"C:\pnav\extra\others\comic"

# Read the HTML file content
with open(html_file_path, 'r', encoding='utf-8') as file:
    soup = BeautifulSoup(file, 'html.parser')

# Extract the title text and sanitize it as folder name
title = soup.title.string.strip()
# Remove special characters except letters, numbers, spaces
folder_name = re.sub(r'[^A-Za-z0-9 ]+', '', title).strip()

# Full path for new folder
new_folder_path = os.path.join(base_folder_path, folder_name)

# Create the folder if it doesn't exist
os.makedirs(new_folder_path, exist_ok=True)
print(f"Folder created at: {new_folder_path}")

# Since file is local, base URL for any relative links should be from file path, so prefix with 'file://'
base_url = f"file://{os.path.abspath(html_file_path)}"

def download_image(url, folder):
    # Skip local file URLs
    if url.startswith('file://'):
        print(f"Skipping local file: {url}")
        return
    try:
        response = requests.get(url)
        if response.status_code == 200:
            filename = os.path.join(folder, url.split("/")[-1])
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"Downloaded: {filename}")
        else:
            print(f"Failed to download {url} with status code {response.status_code}")
    except Exception as e:
        print(f"Error downloading {url}: {e}")

# Find all img tags with data-src attribute and download if jpg
for img in soup.find_all('img'):
    data_src = img.get('data-src')
    if data_src and data_src.lower().endswith('.jpg'):
        img_url = urljoin(base_url, data_src)
        download_image(img_url, new_folder_path)

# Find all a tags with href attribute linking to jpg images and download
for a in soup.find_all('a'):
    href = a.get('href')
    if href and href.lower().endswith('.jpg'):
        img_url = urljoin(base_url, href)
        download_image(img_url, new_folder_path)
