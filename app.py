import sys
import tempfile
from pathlib import Path

import gradio as gr

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import video_downloader.downloader as dl_mod
from video_downloader.downloader import download
from video_downloader.race_controller import ExtractionRaceController
from video_downloader.router import identify


def extract_and_download(url: str, quality: str):
    cleaned = (url or "").strip()
    if not cleaned:
        raise gr.Error("Please paste a valid URL.")

    route = identify(cleaned)
    req_quality = None if quality == "best" else quality

    controller = ExtractionRaceController(
        url=cleaned,
        requested_quality=req_quality,
        no_browser=True,
        prefer_gui=False,
    )
    result = controller.run_race()

    if not result.candidate:
        raise gr.Error("No downloadable media found for this URL.")

    dl_dir = Path(tempfile.mkdtemp(prefix="toolkit_hf_"))
    orig_get_dir = dl_mod.get_download_dir
    dl_mod.get_download_dir = lambda: dl_dir
    try:
        out_path = download(
            result.candidate,
            filename=result.candidate.metadata.get("title", "video"),
            requested_quality=req_quality,
            conflict_policy="replace",
        )
    finally:
        dl_mod.get_download_dir = orig_get_dir

    if not out_path or not Path(out_path).is_file():
        raise gr.Error("Extraction succeeded, but downloading the stream failed.")

    file_str = str(out_path)
    status = (
        f"Platform: **{route.name}** (`{route.media_type}`) | "
        f"Winner: **{result.winner_engine}** in **{result.duration_ms} ms**"
    )
    return status, file_str, file_str


with gr.Blocks(title="Tool-Kit Media Extractor") as demo:
    gr.Markdown("# Tool-Kit Media Extractor\nExtract & download videos from X/Twitter, YouTube, Vimeo, and more.")
    with gr.Row():
        url_input = gr.Textbox(
            label="Media URL",
            placeholder="https://x.com/user/status/1234567890",
            scale=4,
        )
        quality_input = gr.Dropdown(
            choices=["best", "1080p", "720p", "480p", "worst"],
            value="best",
            label="Quality",
            scale=1,
        )
    run_btn = gr.Button("Extract & Download", variant="primary")
    status_md = gr.Markdown()
    video_preview = gr.Video(label="Preview")
    file_output = gr.File(label="Download File")

    run_btn.click(
        fn=extract_and_download,
        inputs=[url_input, quality_input],
        outputs=[status_md, video_preview, file_output],
    )

if __name__ == "__main__":
    demo.launch(ssr_mode=False)
