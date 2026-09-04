#!/usr/bin/env python3
"""Build per-scene ASS captions with audio waveform energy alignment."""
from __future__ import annotations

import json
import math
import re
import struct
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _ass_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        s += 1
        cs = 0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def get_audio_segments(wav_path: Path | None) -> list[tuple[float, float]]:
    """Detect voice speech intervals using RMS energy windowing."""
    if not wav_path or not wav_path.exists():
        return []
    try:
        w = wave.open(str(wav_path), "rb")
        rate = w.getframerate()
        nframes = w.getnframes()
        raw = w.readframes(nframes)
        w.close()
        samples = struct.unpack(f"<{nframes}h", raw)
        win = int(rate * 0.04)  # 40ms window
        energies = []
        for i in range(0, len(samples) - win, win):
            chunk = samples[i : i + win]
            rms = math.sqrt(sum(s * s for s in chunk) / len(chunk))
            energies.append(rms)
        thresh = 280
        segments = []
        in_seg = False
        seg_start = 0.0
        silence_count = 0
        for i, e in enumerate(energies):
            t = i * 0.04
            if e > thresh:
                if not in_seg:
                    in_seg = True
                    seg_start = t
                silence_count = 0
            else:
                if in_seg:
                    silence_count += 1
                    if silence_count >= 5:  # 200ms silence marks clause boundary
                        in_seg = False
                        seg_end = t - 0.20
                        if seg_end - seg_start >= 0.25:
                            segments.append((round(seg_start, 2), round(seg_end, 2)))
        if in_seg:
            segments.append((round(seg_start, 2), round(len(energies) * 0.04, 2)))
        return segments
    except Exception as err:
        print(f"[!] Warning reading {wav_path}: {err}")
        return []


def align_clauses(text: str, duration: float, wav_path: Path | None = None) -> list[tuple[float, float, str]]:
    """Split text naturally by punctuation and align with voice waveform."""
    parts = [p.strip() for p in re.split(r"[，。！？；、\n]+", text or "") if p.strip()]
    if not parts:
        return [(0.0, duration, text or "")]
    
    segs = get_audio_segments(wav_path)
    if not segs:
        # Fallback when no audio is found: active voice from 0.20s to dur-0.8s
        active_start = 0.20
        active_end = max(duration - 0.80, 0.60)
        active_dur = active_end - active_start
        total_len = sum(len(p) for p in parts)
        out = []
        cur = active_start
        for p in parts:
            d = active_dur * (len(p) / total_len)
            out.append((round(cur, 2), round(cur + d, 2), p))
            cur += d
        return out

    if len(parts) == len(segs):
        return [(s[0], s[1], p) for s, p in zip(segs, parts)]

    total_len = sum(len(p) for p in parts)
    char_ratios = [len(p) / total_len for p in parts]
    seg_durs = [s[1] - s[0] for s in segs]
    total_seg_dur = sum(seg_durs)

    out = []
    seg_idx = 0
    for part_idx, p in enumerate(parts):
        if part_idx == len(parts) - 1:
            start_t = segs[seg_idx][0] if seg_idx < len(segs) else segs[-1][1]
            end_t = segs[-1][1]
            out.append((start_t, end_t, p))
            break

        target_time = char_ratios[part_idx] * total_seg_dur
        acc_time = 0.0
        start_seg = seg_idx
        while seg_idx < len(segs) - (len(parts) - 1 - part_idx):
            dur = segs[seg_idx][1] - segs[seg_idx][0]
            if acc_time + dur > target_time and acc_time > 0 and (acc_time + dur - target_time) > (target_time - acc_time):
                break
            acc_time += dur
            seg_idx += 1
            if acc_time >= target_time:
                break

        end_seg = max(start_seg, seg_idx - 1)
        start_t = segs[start_seg][0]
        end_t = segs[end_seg][1]
        out.append((start_t, end_t, p))
    return out


def _alignment(position: str, size: int = 180) -> tuple[int, int, int, int, int]:
    """Return Alignment, MarginL, MarginR, MarginV_main, MarginV_key."""
    pos = (position or "bottom_right").lower()
    if pos in ("center_bottom", "center", "host"):
        main_v = int(size) + 130
        return 2, 64, 64, main_v, main_v + 52
    if pos in ("bottom_left", "left"):
        return 3, 220, 48, 72, 128
    return 1, 48, 260, 72, 128


def write_scene_ass(item: dict, duration: float, out_path: Path, wav_path: Path | None = None) -> Path:
    avatar = item.get("avatar") or {}
    size = int(avatar.get("size") or 180)
    align, ml, mr, mv_main, mv_key = _alignment(str(avatar.get("position") or "bottom_right"), size)
    mood = str(item.get("mood") or avatar.get("mood") or "normal")
    # Keywords are context labels, not semantic color coding; keep them neutral.
    key_colour = "&H00D0D0D0"
    narration = item.get("narration") or ""
    keywords = item.get("keywords") or []

    timed_clauses = align_clauses(narration, duration, wav_path)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,Noto Sans CJK SC,48,&H00FFFFFF,&H000000FF,&H90000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,{align},{ml},{mr},{mv_main},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for st, et, clause in timed_clauses:
        # Requirement: Filter "大家好" from on-screen visual subtitles while keeping voice audio
        display_text = clause.strip()
        display_text = re.sub(r"^大家好[，,！!\s]*", "", display_text).strip()
        if not display_text:
            continue
        events.append(f"Dialogue: 0,{_ass_time(st)},{_ass_time(et)},Main,,0,0,0,,{display_text}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return out_path


def build_all_captions(timed_spec: Path, out_dir: Path) -> dict[str, Path]:
    spec = json.loads(timed_spec.read_text(encoding="utf-8"))
    contract_path = spec.get("contract")
    extras = {}
    if contract_path:
        source = Path(contract_path)
        if not source.is_absolute():
            source = ROOT / source
        if source.exists():
            src = json.loads(source.read_text(encoding="utf-8"))
            for s in src.get("scenes") or []:
                extras[str(s.get("scene"))] = s
    cap_dir = out_dir / "captions"
    wav_dir = out_dir / "wav"
    mapping: dict[str, Path] = {}
    for item in spec.get("scenes") or spec.get("shots") or []:
        sid = str(item.get("scene") or item.get("shot", "01"))
        merged = {**extras.get(sid, {}), **item}
        dur = float(merged.get("total_duration_sec") or merged.get("duration_sec") or 5.0)
        wav_path = wav_dir / f"item{sid}_beat01.wav"
        if not wav_path.exists():
            wav_path = ROOT / "outputs" / "pipeline_v2_p0" / "wav" / f"item{sid}_beat01.wav"
        mapping[sid] = write_scene_ass(merged, dur, cap_dir / f"shot_{sid}.ass", wav_path if wav_path.exists() else None)
        print(f"[+] Caption {mapping[sid]}")
    return mapping


if __name__ == "__main__":
    build_all_captions(ROOT / "data" / "shots_timed.json", ROOT / "outputs" / "pipeline_v2_p2")
