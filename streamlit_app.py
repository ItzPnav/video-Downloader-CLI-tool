import sys
import tempfile
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import video_downloader.downloader as dl_mod
from video_downloader.downloader import download
from video_downloader.race_controller import ExtractionRaceController
from video_downloader.router import identify

st.set_page_config(page_title="Tool-Kit Cloud", layout="centered")
st.title("Tool-Kit Media Extractor")

url = st.text_input("Paste URL (X/Twitter, YouTube, Vimeo, etc.)")
quality = st.selectbox("Quality", ["best", "1080p", "720p", "480p", "worst"])

if st.button("Extract & Download", type="primary") and url:
    route = identify(url)
    st.caption(f"Detected platform: **{route.name}** (`{route.media_type}`)")

    with st.spinner("Racing extraction engines..."):
        controller = ExtractionRaceController(
            url=url,
            requested_quality=None if quality == "best" else quality,
            no_browser=True,
            prefer_gui=False,
        )
        result = controller.run_race()

    if not result.candidate:
        st.error("No downloadable media found.")
    else:
        st.success(f"Won by **{result.winner_engine}** in {result.duration_ms} ms")
        with tempfile.TemporaryDirectory() as tmpdir:
            with st.spinner("Downloading stream to cloud buffer..."):
                orig_get_dir = dl_mod.get_download_dir
                dl_mod.get_download_dir = lambda: Path(tmpdir)
                try:
                    out_path = download(
                        result.candidate,
                        filename=result.candidate.metadata.get("title", "video"),
                        requested_quality=None if quality == "best" else quality,
                        conflict_policy="replace",
                    )
                finally:
                    dl_mod.get_download_dir = orig_get_dir

            if out_path and Path(out_path).is_file():
                file_path = Path(out_path)
                st.video(str(file_path))
                with open(file_path, "rb") as f:
                    st.download_button(
                        label=f"Save {file_path.name} to Device",
                        data=f,
                        file_name=file_path.name,
                        mime="video/mp4",
                    )
