#!/usr/bin/env python3
"""itsmepuliyt TikTok Enhancer - CLI & Video Inspector."""

from __future__ import annotations

import argparse
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from tiktok_bypass.mp4_boxes import find_box, header_size, handler_type, parse_boxes
from tiktok_bypass.processor import process_video


def analyze(path: Path) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe not found.")

    cmd = [
        ffprobe,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    info = json.loads(result.stdout)

    raw = path.read_bytes()
    stts_samples = None
    ghost_eight_byte_count = None

    moov = find_box(raw, "moov")
    if moov:
        for trak in parse_boxes(raw, moov.offset + header_size(moov), moov.end):
            if trak.type != "trak":
                continue
            trak_children = parse_boxes(raw, trak.offset + header_size(trak), trak.end)
            mdia = next((b for b in trak_children if b.type == "mdia"), None)
            if not mdia:
                continue
            mdia_children = parse_boxes(raw, mdia.offset + header_size(mdia), mdia.end)
            hdlr = next((b for b in mdia_children if b.type == "hdlr"), None)
            if not hdlr or handler_type(raw, hdlr) != "vide":
                continue
            minf = next((b for b in mdia_children if b.type == "minf"), None)
            if not minf:
                continue
            minf_children = parse_boxes(raw, minf.offset + header_size(minf), minf.end)
            stbl = next((b for b in minf_children if b.type == "stbl"), None)
            if not stbl:
                continue
            stbl_children = parse_boxes(raw, stbl.offset + header_size(stbl), stbl.end)
            stts = next((b for b in stbl_children if b.type == "stts"), None)
            stsz = next((b for b in stbl_children if b.type == "stsz"), None)
            if stts:
                entry_count = struct.unpack(">I", raw[stts.offset + 12 : stts.offset + 16])[0]
                total = 0
                base = stts.offset + 16
                for i in range(entry_count):
                    count = struct.unpack(">I", raw[base + i * 8 : base + i * 8 + 4])[0]
                    total += count
                stts_samples = total
            if stsz:
                sample_size = struct.unpack(">I", raw[stsz.offset + 12 : stsz.offset + 16])[0]
                count = struct.unpack(">I", raw[stsz.offset + 16 : stsz.offset + 20])[0]
                if sample_size == 0 and count > 0:
                    sizes_base = stsz.offset + 20
                    ghost_eight_byte_count = sum(
                        1
                        for i in range(count)
                        if struct.unpack(">I", raw[sizes_base + i * 4 : sizes_base + i * 4 + 4])[0] == 8
                    )
            break

    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    return {
        "path": str(path),
        "size_mb": round(path.stat().st_size / (1024 * 1024), 2),
        "duration_sec": float(info.get("format", {}).get("duration") or 0),
        "width": video.get("width") if video else None,
        "height": video.get("height") if video else None,
        "fps": video.get("r_frame_rate") if video else None,
        "video_bitrate_kbps": round(int(video.get("bit_rate") or 0) / 1000) if video else None,
        "stts_total_samples": stts_samples,
        "ghost_frame_entries_size_8": ghost_eight_byte_count,
        "inflation_detected": bool(stts_samples and ghost_eight_byte_count and ghost_eight_byte_count > 0),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="itsmepuliyt TikTok Enhancer",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    process = sub.add_parser("process", help="Process input video")
    process.add_argument("input", type=Path, help="Input video file")
    process.add_argument("output", type=Path, help="Output MP4 file path")
    process.add_argument("--multiplier", type=int, default=10)
    process.add_argument("--skip-preprocess", action="store_true")
    process.add_argument("--force-reencode", action="store_true")

    analyze_cmd = sub.add_parser("analyze", help="Inspect MP4 metadata")
    analyze_cmd.add_argument("input", type=Path, help="Video file path")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "process":
            result = process_video(
                args.input,
                args.output,
                multiplier=args.multiplier,
                skip_preprocess=args.skip_preprocess,
                copy_if_compatible=not args.force_reencode,
            )
            report = analyze(result)
            print(json.dumps(report, indent=2))
            return 0

        if args.command == "analyze":
            report = analyze(args.input)
            print(json.dumps(report, indent=2))
            return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
