import os
import re
import shutil
import tempfile

import certifi

os.environ.setdefault("SSL_CERT_FILE", certifi.where())

from flask import Flask, render_template, request, send_file, jsonify

import yt_dlp

app = Flask(__name__)

BASE_DIR = os.path.dirname(__file__)

YOUTUBE_URL_RE = re.compile(
    r"^https?://(www\.|m\.)?(youtube\.com/|youtu\.be/)"
)

COOKIES_FILE = os.path.join(BASE_DIR, "cookies.txt")

# Node.js runtime used only for the PO Token provider below (installed via nodeenv,
# see README "PO Token" section) — not required for the app itself.
NODE_BIN = os.path.join(BASE_DIR, ".nodeenv", "bin", "node")

# PO Token provider (bgutil-ytdlp-pot-provider): works around YouTube's SABR /
# "Sign in to confirm you're not a bot" block on the actual video download.
# Requires running, once:
#   cd .bgutil-provider/server && npm install && npm run build
# See README for details. The app falls back gracefully if it's not built yet.
BGUTIL_SERVER_HOME = os.path.join(BASE_DIR, ".bgutil-provider", "server")
BGUTIL_SCRIPT = os.path.join(BGUTIL_SERVER_HOME, "build", "generate_once.js")

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None
POT_PROVIDER_READY = os.path.exists(BGUTIL_SCRIPT) and os.path.exists(NODE_BIN)


def is_valid_youtube_url(url: str) -> bool:
    return bool(url) and bool(YOUTUBE_URL_RE.match(url.strip()))


def base_ydl_opts() -> dict:
    opts = {"quiet": True, "noplaylist": True, "remote_components": ["ejs:github"]}
    if os.path.exists(COOKIES_FILE):
        # Manual override: drop a cookies.txt in the project folder to use it
        # instead of reading Safari's cookie store directly.
        opts["cookiefile"] = COOKIES_FILE
    else:
        # Reads Safari's cookies live, so it's never stale like an exported
        # file. Requires Full Disk Access granted to this app in
        # System Settings > Privacy & Security.
        opts["cookiesfrombrowser"] = ("safari",)
    if os.path.exists(NODE_BIN):
        # Needed both for yt-dlp's own JS runtime (signature decryption) and,
        # when available, the PO Token provider below.
        opts["js_runtimes"] = {"node": {"path": NODE_BIN}}
    if POT_PROVIDER_READY:
        opts["extractor_args"] = {
            "youtubepot-bgutilscript": {"server_home": [BGUTIL_SERVER_HOME]}
        }
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

    if FFMPEG_AVAILABLE:
        video_format = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
    else:
        # No ffmpeg to mux separate video+audio streams, so stick to formats
        # that come as a single already-merged file.
        video_format = "best[protocol!*=m3u8][ext=mp4]/best[protocol!*=m3u8]/best"

    ydl_opts = {
        **base_ydl_opts(),
        "outtmpl": outtmpl,
        "format": video_format,
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
