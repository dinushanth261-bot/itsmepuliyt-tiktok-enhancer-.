 #!/usr/bin/env python3
"""itsmepuliyt TikTok Enhancer - Web Backend Server."""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS

from main import analyze
from tiktok_bypass.processor import process_video

app = Flask(__name__, static_folder="static")
CORS(app)

BASE_DIR = Path(__file__).parent.resolve()
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)


@app.route("/api/status", methods=["GET"])
def get_status():
    ffprobe_path = shutil.which("ffprobe")
    ffmpeg_path = shutil.which("ffmpeg")
    return jsonify({
        "status": "online",
        "app_name": "itsmepuliyt TikTok Enhancer",
        "ffmpeg_available": bool(ffmpeg_path),
        "ffprobe_available": bool(ffprobe_path),
    })


@app.route("/api/analyze", methods=["POST"])
def analyze_video_endpoint():
    file_path = None
    
    if "file" in request.files:
        file = request.files["file"]
        if file.filename:
            file_id = uuid.uuid4().hex[:8]
            ext = Path(file.filename).suffix or ".mp4"
            save_path = UPLOAD_DIR / f"input_{file_id}{ext}"
            file.save(save_path)
            file_path = save_path
    elif request.is_json and "path" in request.json:
        file_path = Path(request.json["path"])
    
    if not file_path or not file_path.exists():
        return jsonify({"error": "No valid video file provided"}), 400

    try:
        report = analyze(file_path)
        report["filename"] = file_path.name
        return jsonify({"success": True, "data": report})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/process", methods=["POST"])
def process_video_endpoint():
    try:
        multiplier = int(request.form.get("multiplier", 10))
        skip_preprocess = request.form.get("skip_preprocess", "false").lower() == "true"
        force_reencode = request.form.get("force_reencode", "false").lower() == "true"

        input_path = None
        if "file" in request.files and request.files["file"].filename:
            file = request.files["file"]
            file_id = uuid.uuid4().hex[:8]
            safe_name = Path(file.filename).stem
            ext = Path(file.filename).suffix or ".mp4"
            input_path = UPLOAD_DIR / f"{safe_name}_{file_id}{ext}"
            file.save(input_path)
        elif request.form.get("existing_file"):
            input_path = UPLOAD_DIR / request.form.get("existing_file")

        if not input_path or not input_path.exists():
            return jsonify({"error": "No video file uploaded or found"}), 400

        output_filename = f"ITSMEPULIYT_ENHANCED_{input_path.stem}.mp4"
        output_path = OUTPUT_DIR / output_filename

        processed_result = process_video(
            input_path,
            output_path,
            multiplier=multiplier,
            skip_preprocess=skip_preprocess,
            copy_if_compatible=not force_reencode,
        )

        analysis = analyze(processed_result)

        return jsonify({
            "success": True,
            "message": "itsmepuliyt TikTok Enhancer process completed successfully!",
            "input_filename": input_path.name,
            "output_filename": output_filename,
            "download_url": f"/api/download/{output_filename}",
            "stream_input_url": f"/api/stream/uploads/{input_path.name}",
            "stream_output_url": f"/api/stream/outputs/{output_filename}",
            "analysis": analysis,
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/download/<filename>", methods=["GET"])
def download_file(filename):
    target = OUTPUT_DIR / filename
    if not target.exists():
        return jsonify({"error": "File not found"}), 404
    return send_file(target, as_attachment=True)


@app.route("/api/stream/<folder>/<filename>", methods=["GET"])
def stream_file(folder, filename):
    target_dir = UPLOAD_DIR if folder == "uploads" else OUTPUT_DIR
    target = target_dir / filename
    if not target.exists():
        return jsonify({"error": "File not found"}), 404
    return send_file(target, mimetype="video/mp4")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
