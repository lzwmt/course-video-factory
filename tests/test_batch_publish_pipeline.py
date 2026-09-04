#!/usr/bin/env python3
"""Unit tests for V6 batch / publish / ducking / delivery helpers."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.audio_ducking import ducking_filter_complex, pick_bgm  # noqa: E402
from scripts.cache_fingerprint import compute_fingerprint, plan_skips, save_cache  # noqa: E402
from scripts.package_publisher import build_chapter_markers, build_publish_meta, format_ts  # noqa: E402
from scripts.sync_delivery import expand_env, load_delivery_config  # noqa: E402


SPEC = {
    "title": "从零扩展到百万用户",
    "template": "system_evolution",
    "target_duration_sec": 79.5,
    "scenes": [
        {"scene": "00", "title": "痛点引入", "narration": "大家好", "keywords": ["高并发"], "total_duration_sec": 25},
        {
            "scene": "01",
            "title": "单机瓶颈",
            "narration": "单机扛不住",
            "graph": {"nodes": ["single"]},
            "actions": [{"type": "node", "id": "single", "at": 0.5}],
            "total_duration_sec": 45,
        },
    ],
}


class FingerprintTests(unittest.TestCase):
    def test_narration_visual_config_are_independent(self):
        base = compute_fingerprint(SPEC, {"theme": {"primary_color": "#3B82F6"}}, {}, root=ROOT)
        narr = json.loads(json.dumps(SPEC))
        narr["scenes"][0]["narration"] = "改口播"
        nfp = compute_fingerprint(narr, {"theme": {"primary_color": "#3B82F6"}}, {}, root=ROOT)
        vis = json.loads(json.dumps(SPEC))
        vis["scenes"][1]["graph"] = {"nodes": ["lb"]}
        vfp = compute_fingerprint(vis, {"theme": {"primary_color": "#3B82F6"}}, {}, root=ROOT)
        cfg = compute_fingerprint(SPEC, {"theme": {"primary_color": "#EF4444"}}, {}, root=ROOT)
        self.assertNotEqual(base["narration_hash"], nfp["narration_hash"])
        self.assertEqual(base["visual_hash"], nfp["visual_hash"])
        self.assertNotEqual(base["visual_hash"], vfp["visual_hash"])
        self.assertEqual(base["narration_hash"], vfp["narration_hash"])
        self.assertNotEqual(base["config_hash"], cfg["config_hash"])
        self.assertEqual(base["narration_hash"], cfg["narration_hash"])

    def test_plan_skips_force_and_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            fp = compute_fingerprint(SPEC, {}, {}, root=ROOT)
            forced = plan_skips(out, fp, force=True)
            self.assertFalse(forced["tts"])
            (out / "shots_timed.json").write_text("{}", encoding="utf-8")
            (out / "voice.wav").write_bytes(b"RIFF")
            (out / "lecture_courseware.mp4").write_bytes(b"mp4")
            (out / "dh.mp4").write_bytes(b"mp4")
            (out / "final.mp4").write_bytes(b"mp4")
            save_cache(out, fp)
            cached = plan_skips(out, fp, force=False)
            self.assertTrue(cached["all"])
            self.assertTrue(cached["tts"])
            self.assertTrue(cached["render"])


class PublisherTests(unittest.TestCase):
    def test_markers_and_platforms(self):
        self.assertEqual(format_ts(0), "00:00")
        self.assertEqual(format_ts(25), "00:25")
        self.assertEqual(format_ts(70), "01:10")
        markers = build_chapter_markers(SPEC)
        self.assertEqual(markers[0], {"time": "00:00", "title": "痛点引入"})
        self.assertEqual(markers[1]["time"], "00:25")
        meta = build_publish_meta(
            "system-design",
            "01",
            SPEC,
            duration=79.5,
            course_info={"theme": {"badge_prefix": "系统设计全书"}},
        )
        self.assertEqual(meta["course_id"], "system-design")
        self.assertEqual(meta["chapter_id"], "01")
        self.assertEqual(meta["durations"], 79.5)
        self.assertIn("bilibili", meta["platforms"])
        self.assertIn("xiaohongshu", meta["platforms"])
        self.assertIn("douyin", meta["platforms"])
        self.assertEqual(meta["platforms"]["bilibili"]["cover"], "cover_bilibili.png")
        self.assertIn("时间轴", meta["platforms"]["bilibili"]["desc"])
        self.assertEqual(meta["chapter_markers"], markers)


class DuckingTests(unittest.TestCase):
    def test_filter_and_template_pick(self):
        filt = ducking_filter_complex()
        self.assertIn("sidechaincompress=threshold=0.08:ratio=6:attack=20:release=350", filt)
        self.assertIn("[0:a]asplit=2[voice_main][voice_side]", filt)
        self.assertIn("volume=0.35", filt)
        self.assertEqual(pick_bgm({"template": "algorithm"}), "tech_ambient_fast.mp3")
        self.assertEqual(pick_bgm({"template": "estimation"}), "upbeat_inspiration.mp3")
        self.assertEqual(pick_bgm({"template": "system_evolution"}), "tech_calm_deep.mp3")

    def test_ffmpeg_sidechain_mix(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            voice = tmp_path / "voice.wav"
            bgm = tmp_path / "bgm.wav"
            video = tmp_path / "clip.mp4"
            out = tmp_path / "out.mp4"
            subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", str(voice)],
                check=True, capture_output=True,
            )
            subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi", "-i", "anoisesrc=color=brown:duration=2", str(bgm)],
                check=True, capture_output=True,
            )
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "lavfi", "-i", "color=c=black:s=320x240:d=2",
                    "-i", str(voice),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    str(video),
                ],
                check=True, capture_output=True,
            )
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", str(video), "-i", str(bgm),
                    "-filter_complex", ducking_filter_complex(),
                    "-map", "0:v", "-map", "[aout]",
                    "-c:v", "copy", "-c:a", "aac", "-shortest",
                    str(out),
                ],
                check=True, capture_output=True,
            )
            self.assertGreater(out.stat().st_size, 1000)


class DeliveryTests(unittest.TestCase):
    def test_env_interpolation(self):
        os.environ["FEISHU_WEBHOOK_URL"] = "https://example.test/hook"
        text = expand_env('{"url": "${FEISHU_WEBHOOK_URL}"}')
        self.assertIn("https://example.test/hook", text)
        cfg = load_delivery_config(ROOT / "config" / "delivery.json")
        self.assertEqual(cfg["targets"]["mac"]["type"], "scp")
        self.assertEqual(cfg["targets"]["mac"]["remote_dir"], "~/Downloads/")
        self.assertEqual(cfg["targets"]["nas"]["type"], "rsync")
        self.assertEqual(cfg["webhooks"][0]["name"], "feishu")
        self.assertEqual(cfg["webhooks"][0]["url"], "https://example.test/hook")


class CliSmokeTests(unittest.TestCase):
    def test_help_flags(self):
        for script, flag in [
            ("scripts/batch_produce.py", "--all"),
            ("scripts/package_publisher.py", "--dir"),
            ("scripts/sync_delivery.py", "--target"),
        ]:
            r = subprocess.run(
                [sys.executable, str(ROOT / script), "-h"],
                capture_output=True, text=True, check=True,
            )
            self.assertIn(flag, r.stdout)


if __name__ == "__main__":
    unittest.main()
