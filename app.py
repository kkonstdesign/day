import os
import re
import shutil
import tempfile

from flask import Flask, render_template, request, send_file, jsonify

import yt_dlp

app = Flask(__name__)

YOUTUBE_URL_RE = re.compile(
    r"^https?://(www\.|m\.)?(youtube\.com/|youtu\.be/)"
)

COOKIES_FILE = os.path.join(os.path.dirname(__file__), "cookies.txt")


def is_valid_youtube_url(url: str) -> bool:
    return bool(url) and bool(YOUTUBE_URL_RE.match(url.strip()))


def base_ydl_opts() -> dict:
    opts = {"quiet": True, "noplaylist": True}
    if os.path.exists(COOKIES_FILE):
        opts["cookiefile"] = COOKIES_FILE
    return opts


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/info", methods=["POST"])
def video_info():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()

    if not is_valid_youtube_url(url):
        return jsonify({"error": "Введите корректную ссылку на YouTube"}), 400

    ydl_opts = {**base_ydl_opts(), "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        return jsonify({"error": f"Не удалось получить информацию о видео: {exc}"}), 400

    return jsonify(
        {
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "uploader": info.get("uploader"),
        }
    )


@app.route("/download")
def download():
    url = (request.args.get("url") or "").strip()

    if not is_valid_youtube_url(url):
        return jsonify({"error": "Введите корректную ссылку на YouTube"}), 400

    tmp_dir = tempfile.mkdtemp(prefix="ytdl_")
    outtmpl = os.path.join(tmp_dir, "%(title).150s.%(ext)s")

    ydl_opts = {
        **base_ydl_opts(),
        "outtmpl": outtmpl,
        "format": "best[ext=mp4]/best",
        "restrictfilenames": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
    except Exception as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return jsonify({"error": f"Ошибка скачивания: {exc}"}), 400

    if not os.path.exists(filename):
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return jsonify({"error": "Файл не найден после скачивания"}), 500

    response = send_file(
        filename,
        as_attachment=True,
        download_name=os.path.basename(filename),
    )
    response.call_on_close(lambda: shutil.rmtree(tmp_dir, ignore_errors=True))
    return response


if __name__ == "__main__":
    app.run(debug=True, port=5001)
