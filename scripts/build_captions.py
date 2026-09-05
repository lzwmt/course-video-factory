#!/usr/bin/env python3
"""Build per-scene ASS captions with audio waveform energy alignment and fixed layout."""
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


def _sanitize_caption_source(text: str) -> str:
    s = re.sub(r"<[^>]+>", " ", text or "")
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", s)
    s = re.sub(r"\[[^\]]*\]\([^)]*\)", " ", s)
    s = re.sub(r"[#*_`>]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def smart_chunk_clauses(text: str) -> list[str]:
    """Split text into balanced, readable chunks (8-16 chars) for steady on-screen display."""
    clean = _sanitize_caption_source(text)
    sentences = [s.strip() for s in re.split(r"[。！？；\n]+", clean) if s.strip()]
    chunks: list[str] = []
    for sent in sentences:
        clauses = [c.strip() for c in re.split(r"[，,：:、]+", sent) if c.strip()]
        cur = ""
        for clause in clauses:
            if not cur:
                cur = clause
            elif len(cur) + len(clause) + 1 <= 16:
                cur += "，" + clause
            else:
                chunks.append(cur)
                cur = clause
        if cur:
            chunks.append(cur)

    balanced: list[str] = []
    for c in chunks:
        if not balanced:
            balanced.append(c)
        elif len(c) < 8 and len(balanced[-1]) + len(c) + 1 <= 24:
            balanced[-1] += "，" + c
        elif len(balanced[-1]) < 8 and len(balanced[-1]) + len(c) + 1 <= 24:
            balanced[-1] += "，" + c
        else:
            balanced.append(c)

    final_chunks: list[str] = []
    for b in balanced:
        if len(b) <= 18:
            final_chunks.append(b)
        else:
            comma = b.find("，", 7, 14)
            if comma != -1:
                final_chunks.append(b[:comma])
                final_chunks.append(b[comma + 1:])
            else:
                mid = len(b) // 2
                final_chunks.append(b[:mid])
                final_chunks.append(b[mid:])
    return final_chunks


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
    """Generate smooth, steady, non-flickering subtitle intervals."""
    parts = smart_chunk_clauses(text)
    if not parts:
        return [(0.0, duration, text or "")]

    total_len = sum(len(p) for p in parts)
    segs = get_audio_segments(wav_path)
    if segs and len(segs) >= 2:
        speech_start = max(0.12, segs[0][0])
        speech_end = min(duration - 0.15, segs[-1][1])
    else:
        speech_start = 0.20
        speech_end = max(duration - 0.40, 0.80)

    total_speech_dur = max(speech_end - speech_start, 0.5)
    out: list[tuple[float, float, str]] = []
    cur_t = speech_start
    for p in parts:
        weight = len(p) / max(total_len, 1)
        chunk_dur = total_speech_dur * weight
        st = cur_t
        et = cur_t + chunk_dur
        display = p.strip("，,：:、 ").strip()
        out.append((round(st, 2), round(et, 2), display))
        cur_t = et
    return out


def write_scene_ass(item: dict, duration: float, out_path: Path, wav_path: Path | None = None) -> Path:
    """Write fixed-position, high-legibility ASS subtitles."""
    narration = item.get("narration") or ""
    timed_clauses = align_clauses(narration, duration, wav_path)

    # Fixed layout parameters:
    # PlayRes: 1080 x 1920
    # Alignment: 2 (Bottom-Center)
    # MarginV: 390 (Fixed height from bottom: perfectly positioned in reading area above bottom avatar)
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,Noto Sans CJK SC,48,&H00FFFFFF,&H000000FF,&H90000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,64,64,390,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for st, et, clause in timed_clauses:
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
    cap_dir = out_dir / "captions"
    wav_dir = out_dir / "wav"
    mapping: dict[str, Path] = {}
    for item in spec.get("scenes") or spec.get("shots") or []:
        sid = str(item.get("scene") or item.get("shot", "01"))
        dur = float(item.get("total_duration_sec") or item.get("duration_sec") or 5.0)
        wav_path = wav_dir / f"item{sid}_beat01.wav"
        if not wav_path.exists() and sid.isdigit():
            p_id = f"{int(sid):02d}"
            u_id = f"{int(sid)}"
            for cand in (
                wav_dir / f"item{p_id}_beat01.wav",
                wav_dir / f"item{u_id}_beat01.wav",
                wav_dir / f"item{p_id}_beat1.wav",
                wav_dir / f"item{u_id}_beat1.wav",
            ):
                if cand.exists():
                    wav_path = cand
                    break
        actual_wav = wav_path if wav_path.exists() else None
        mapping[sid] = write_scene_ass(item, dur, cap_dir / f"shot_{sid}.ass", actual_wav)
        print(f"[+] Caption {mapping[sid]}")
    return mapping


if __name__ == "__main__":
    build_all_captions(ROOT / "data" / "shots_timed.json", ROOT / "outputs" / "pipeline_v2_p2")
