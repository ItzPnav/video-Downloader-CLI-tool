"""
Unit and Integration Tests for X/Twitter Video Extraction Engine (ported from twitter-dl).
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Add src to sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import video_downloader.extractors.twitter as twitter_core
from video_downloader.extractors.twitter import (
    DownloadError,
    FetchError,
    InvalidURLError,
    NoVideoError,
    TweetRef,
    Variant,
    Video,
    _info_from_fxtwitter,
    _info_from_syndication,
    _syndication_token,
    _variants_from_formats,
    ensure_media_url,
    extract_twitter_candidate,
    fetch_info,
    is_twitter_url,
    parse_url,
)
from video_downloader.router import identify
from video_downloader.static_scanner import StaticScanner


def make_video() -> Video:
    return Video(
        index=0,
        duration_s=10,
        thumbnail=None,
        variants=[
            Variant(1080, 1920, 2176, "https://video.twimg.com/a.mp4"),
            Variant(720, 1280, 832, "https://video.twimg.com/b.mp4"),
            Variant(320, 568, 256, "https://video.twimg.com/c.mp4"),
        ],
    )


SYND = {
    "text": "hello",
    "user": {"name": "Mr H", "screen_name": "MrH_Hen"},
    "mediaDetails": [
        {
            "type": "video",
            "media_url_https": "https://pbs.twimg.com/x.jpg",
            "video_info": {
                "duration_millis": 5000,
                "variants": [
                    {
                        "content_type": "application/x-mpegURL",
                        "url": "https://video.twimg.com/a.m3u8",
                    },
                    {
                        "bitrate": 832000,
                        "content_type": "video/mp4",
                        "url": "https://video.twimg.com/v/avc1/480x852/a.mp4",
                    },
                    {
                        "bitrate": 2176000,
                        "content_type": "video/mp4",
                        "url": "https://video.twimg.com/v/avc1/720x1280/b.mp4",
                    },
                ],
            },
        }
    ],
}
REF = TweetRef("MrH_Hen", "2120373955278348336")


class TestTwitterExtractor(unittest.TestCase):

    def test_valid_url_forms(self):
        for url in (
            "https://x.com/jack/status/20",
            "https://twitter.com/jack/status/20?s=46",
            "  https://www.x.com/jack/status/20  ",
            "https://mobile.twitter.com/i/status/20",
            "https://x.com/i/web/status/20",
            "https://fxtwitter.com/jack/status/20",
            "https://vxtwitter.com/jack/status/20/video/2",
        ):
            with self.subTest(url=url):
                self.assertTrue(is_twitter_url(url))
                ref = parse_url(url)
                self.assertEqual(ref.tweet_id, "20")

        ref_idx = parse_url("https://x.com/jack/status/20/video/2")
        self.assertEqual(ref_idx.video_index, 2)

    def test_invalid_urls(self):
        for url in ("", "https://example.com/a/status/1", "https://x.com/jack", "nope"):
            with self.subTest(url=url):
                with self.assertRaises(InvalidURLError):
                    parse_url(url)

    def test_router_matches_twitter(self):
        for url in (
            "https://x.com/jack/status/20",
            "https://twitter.com/jack/status/20",
            "https://mobile.twitter.com/jack/status/20",
            "https://fxtwitter.com/jack/status/20",
            "https://t.co/abcd1234",
        ):
            route = identify(url)
            self.assertEqual(route.platform, "twitter")
            self.assertEqual(route.media_type, "video")

    def test_pick_quality(self):
        v = make_video()
        self.assertEqual(v.pick("best").height, 1080)
        self.assertEqual(v.pick("worst").height, 320)
        self.assertEqual(v.pick("720").height, 720)
        self.assertEqual(v.pick("900p").height, 720)
        self.assertEqual(v.pick(100).height, 320)  # falls back to smallest

        with self.assertRaises(ValueError):
            v.pick("medium")
        with self.assertRaises(NoVideoError):
            Video(0, None, None, []).pick("best")

    def test_media_host_guard(self):
        ensure_media_url("https://video.twimg.com/x.mp4")
        for url in (
            "https://evil.com/x.mp4",
            "https://twimg.com.evil.com/x.mp4",
            "http://localhost/x",
        ):
            with self.subTest(url=url):
                with self.assertRaises(DownloadError):
                    ensure_media_url(url)

    def test_format_filter_keeps_only_direct_mp4(self):
        formats = [
            {"format_id": "hls", "protocol": "m3u8_native", "ext": "mp4", "vcodec": "avc1", "url": "u1"},
            {"format_id": "http-832", "protocol": "https", "ext": "mp4", "vcodec": "avc1", "height": 720, "tbr": 832, "url": "u2"},
            {"format_id": "dup", "protocol": "https", "ext": "mp4", "vcodec": "avc1", "height": 720, "tbr": 832, "url": "u2"},
            {"format_id": "audio", "protocol": "https", "ext": "mp4", "vcodec": "none", "url": "u3"},
        ]
        out = _variants_from_formats(formats)
        self.assertEqual([v.url for v in out], ["u2"])

    def test_syndication_token_and_embed_parse(self):
        tok = _syndication_token(REF.tweet_id)
        self.assertTrue(tok.isalnum())

        info = _info_from_syndication(REF, SYND)
        v = info.videos[0]
        self.assertEqual([x.height for x in v.variants], [1280, 852])
        self.assertEqual(info.source, "embed")

        # Quoted tweet fallback
        info_qt = _info_from_syndication(REF, {"text": "qt", "quoted_tweet": SYND})
        self.assertEqual(len(info_qt.videos), 1)

        # Tombstone error
        with self.assertRaises(FetchError):
            _info_from_syndication(REF, {"__typename": "TweetTombstone"})

    def test_fxtwitter_parse_and_fallback_order(self):
        data = {
            "tweet": {
                "text": "x",
                "author": {"name": "A"},
                "media": {
                    "videos": [
                        {
                            "url": "https://video.twimg.com/b.mp4",
                            "height": 720,
                            "width": 1280,
                            "duration": 3,
                        }
                    ]
                },
            }
        }
        info = _info_from_fxtwitter(REF, data)
        self.assertEqual(info.videos[0].variants[0].height, 720)

        boom = mock.Mock(side_effect=FetchError("nope"))
        with mock.patch.object(
            twitter_core,
            "_SOURCES",
            (("a", boom), ("b", boom), ("c", mock.Mock(return_value=info))),
        ):
            res = fetch_info("https://x.com/MrH_Hen/status/2120373955278348336")
        self.assertEqual(res.source, "fxtwitter")
        self.assertEqual(boom.call_count, 2)

    def test_extract_twitter_candidate_and_static_scanner_wiring(self):
        fake_info = _info_from_syndication(REF, SYND)
        with mock.patch.object(twitter_core, "fetch_info", return_value=fake_info):
            cand = extract_twitter_candidate(
                "https://x.com/MrH_Hen/status/2120373955278348336",
                requested_quality="900p",
            )
            self.assertIsNotNone(cand)
            self.assertEqual(cand.metadata["height"], 852)
            self.assertEqual(cand.source, "twitter:embed")
            self.assertEqual(cand.score, 100)
            self.assertTrue(cand.url.startswith("https://video.twimg.com/"))

            # Verify StaticScanner delegates Twitter URLs and honors requested_quality
            scanner = StaticScanner(
                "https://x.com/MrH_Hen/status/2120373955278348336",
                requested_quality="900p",
            )
            results = scanner.scan()
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].metadata["height"], 852)


if __name__ == "__main__":
    unittest.main()
