#!/usr/bin/env python3
"""Synthesize TTS audio per beat/scene and write timed specification JSON."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.presenter_paths import studio_root, studio_site_packages

EDGE_VOICES = {
    "yunxi": "zh-CN-YunxiNeural",
    "yunyang": "zh-CN-YunyangNeural",
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",
}


def _attach_studio() -> None:
    studio = studio_root()
    site = studio_site_packages(studio)
    if site is not None and str(site) not in sys.path:
        sys.path.insert(0, str(site))
    if studio is not None and str(studio) not in sys.path:
        sys.path.insert(0, str(studio))


def _synthesize_edge(text: str, raw_wav: Path, speaker: str) -> None:
    voice = EDGE_VOICES.get(speaker.lower(), speaker if "-" in speaker else "zh-CN-YunxiNeural")
    try:
        import asyncio
        import edge_tts
    except ImportError as exc:
        raise RuntimeError("edge-tts is required for --skip-presenter TTS: pip install edge-tts") from exc

    async def _run() -> None:
        comm = edge_tts.Communicate(text, voice)
        await comm.save(str(raw_wav))

    asyncio.run(_run())

def ffprobe_duration(path: Path) -> float:
    """Get accurate audio duration in seconds."""
    r = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path)
        ],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())

def clean_narration_for_tts(text: str) -> str:
    """Normalize text for natural and stable speech synthesis."""
    t = text.replace("➔", "，到，").replace("->", "，到，")
    t = t.replace("：", "，").replace("§", "第")
    t = t.replace("100%", "百分之百").replace("80%", "百分之八十")
    return t.strip()

def build_timed_shots(
    spec_path: Path,
    output_dir: Path,
    engine: str = "edge",
    speaker: str = "yunxi",
    force_tts: bool = False,
) -> dict:
    """Run TTS for all beats/scenes in spec, measure duration, and produce unified voice.wav."""
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    wav_dir = output_dir / "wav"
    wav_dir.mkdir(parents=True, exist_ok=True)

    engine_l = engine.lower()
    tts = None
    if engine_l == "qwen":
        _attach_studio()
        from core.tts.tts_engine import create_tts_engine
        tts = create_tts_engine(engine)

    items = spec.get("scenes") or spec.get("shots") or []
    is_scene_mode = "scenes" in spec

    wavs: list[Path] = []
    idx = 0
    total_sec = 0.0

    print(f"[*] Processing spec: {spec.get('id', 'spec')} ({len(items)} {'scenes' if is_scene_mode else 'shots'}) with TTS [{engine}:{speaker}]")

    for item in items:
        item_id = str(item.get("scene") or item.get("shot", f"{idx:02d}"))
        item_title = item.get("title", "")
        item_sec = 0.0
        prefix = "Scene" if is_scene_mode else "Shot"
        print(f"  [{prefix} {item_id}] {item_title}")

        # Normalize beats
        if "beats" in item and isinstance(item["beats"], list) and len(item["beats"]) > 0:
            beats = item["beats"]
        else:
            beats = [{"beat": 1, "narration": item.get("narration", "")}]
            item["beats"] = beats

        for b_idx, beat in enumerate(beats, 1):
            idx += 1
            raw_wav = wav_dir / f"item{item_id}_beat{b_idx:02d}_raw.wav"
            clean_wav = wav_dir / f"item{item_id}_beat{b_idx:02d}.wav"
            
            # Synthesize if needed
            if force_tts or not clean_wav.exists() or clean_wav.stat().st_size == 0:
                raw_text = beat.get("narration", "")
                clean_text = clean_narration_for_tts(raw_text)
                print(f"    -> Synthesizing beat {b_idx}: {clean_text[:35]}...")
                
                if engine_l == "qwen":
                    tts.synthesize(
                        clean_text,
                        str(raw_wav),
                        speaker=speaker,
                        temperature=0.35,
                        repetition_penalty=1.15,
                        seed=42,
                    )
                else:
                    _synthesize_edge(clean_text, raw_wav, speaker)
                
                # Standardize to 24000Hz 16-bit mono WAV
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-i", str(raw_wav),
                        "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le",
                        str(clean_wav)
                    ],
                    check=True, capture_output=True
                )
                if raw_wav.exists():
                    raw_wav.unlink()

            dur = round(ffprobe_duration(clean_wav), 3)
            beat["duration_sec"] = dur
            item_sec += dur
            wavs.append(clean_wav)
            print(f"    -> Beat {b_idx}: {dur:.2f}s")

        item["duration_sec"] = round(item_sec, 3)
        item["total_duration_sec"] = round(item_sec, 3)
        # Ensure shot field exists for renderer compatibility
        if "shot" not in item and "scene" in item:
            item["shot"] = item["scene"]
        total_sec += item_sec

    spec["total_duration_sec"] = round(total_sec, 3)
    if "scenes" in spec and "shots" not in spec:
        spec["shots"] = spec["scenes"]

    # Write timed spec
    timed_spec_path = output_dir / "shots_timed.json"
    timed_spec_json = json.dumps(spec, ensure_ascii=False, indent=2)
    timed_spec_path.write_text(timed_spec_json, encoding="utf-8")
    if spec.get("id") == "ch1-v2-sample":
        (ROOT / "data" / "shots_timed.json").write_text(timed_spec_json, encoding="utf-8")
    print(f"[+] Wrote timed spec to {timed_spec_path} (Total duration: {total_sec:.2f}s)")

    # Concatenate all wavs into voice.wav
    wav_concat_list = output_dir / "wav_concat.txt"
    wav_concat_list.write_text("".join(f"file '{w.resolve()}'\n" for w in wavs), encoding="utf-8")
    
    voice_wav = output_dir / "voice.wav"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(wav_concat_list),
            "-c:a", "pcm_s16le", "-ar", "24000", "-ac", "1",
            str(voice_wav)
        ],
        check=True,
    )
    print(f"[+] Concatenated {len(wavs)} audio clips into {voice_wav}")

    return spec

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", default=str(ROOT / "data" / "ch1-v2-scenes.json"), help="Specification JSON")
    parser.add_argument("--out", default=str(ROOT / "outputs" / "pipeline"), help="Output directory")
    parser.add_argument("--engine", default="edge", choices=["edge", "qwen"], help="TTS engine")
    parser.add_argument("--speaker", default="yunxi", help="Speaker name (yunxi/yunyang/xiaoxiao for edge, ryan for qwen)")
    parser.add_argument("--force", action="store_true", help="Force re-synthesizing all audio")
    args = parser.parse_args()

    build_timed_shots(
        spec_path=Path(args.spec),
        output_dir=Path(args.out),
        engine=args.engine,
        speaker=args.speaker,
        force_tts=args.force,
    )
