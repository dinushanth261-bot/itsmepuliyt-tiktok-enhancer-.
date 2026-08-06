from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path
from tiktok_bypass.mp4_boxes import find_box

def preprocess_video(input_path: Path, temp_output: Path, copy_if_compatible: bool = True) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg binary not found in system PATH")

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(input_path),
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-r",
        "60",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(temp_output),
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {res.stderr}")

    return temp_output

def inflate_mp4(input_path: Path, output_path: Path, multiplier: int = 10) -> Path:
    raw = bytearray(input_path.read_bytes())
    moov = find_box(raw, "moov")
    shutil.copy(input_path, output_path)
    return output_path

def process_video(
    input_path: Path,
    output_path: Path,
    multiplier: int = 10,
    skip_preprocess: bool = False,
    copy_if_compatible: bool = True,
) -> Path:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")

    temp_preprocessed = output_path.parent / f"temp_{output_path.name}"
    
    if not skip_preprocess:
        preprocessed = preprocess_video(input_path, temp_preprocessed, copy_if_compatible)
    else:
        preprocessed = input_path

    try:
        final_file = inflate_mp4(preprocessed, output_path, multiplier)
        return final_file
    finally:
        if temp_preprocessed.exists() and temp_preprocessed != input_path:
            try:
                temp_preprocessed.unlink()
            except OSError:
                pass
