
import os
import re
import glob
import socket
import shutil
import tempfile
import subprocess
import ipaddress
from urllib.parse import urlparse

from flask import (
    Flask, request, render_template_string,
    send_file, after_this_request
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["20 per hour"],
    storage_uri="memory://"
)

HTML = """
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Descargador de vídeos</title>
<style>
body {
  font-family:Arial,sans-serif;background:#101827;color:white;
  margin:0;padding:24px
}
main {
  max-width:520px;margin:60px auto;text-align:center
}
input,button {
  box-sizing:border-box;width:100%;padding:15px;
  margin-top:12px;border-radius:10px;font-size:16px
}
input {
  border:1px solid #526078;background:#202c40;color:white
}
button {
  background:#3675f5;color:white;border:0;font-weight:bold
}
p {color:#b8c4d8;line-height:1.5}
</style>
</head>
<body><main>
<h1>Descargador de vídeos</h1>
<p>Pega un enlace de un vídeo que tengas permiso para descargar.</p>
<form method="post" action="/download">
<input name="url" type="url" placeholder="https://..." required>
<button type="submit">Descargar vídeo</button>
</form>
<p>Se admiten sitios compatibles. Límite: 100 MB por archivo.
El procesamiento puede tardar.</p>
</main></body></html>
"""


def valid_url(url):
    try:
        parsed = urlparse(url)
        host = parsed.hostname

        if parsed.scheme != "https" or not host:
            return False

        if parsed.username or parsed.password:
            return False

        if host == "localhost" or host.endswith(".localhost"):
            return False

        addresses = socket.getaddrinfo(
            host, parsed.port or 443, type=socket.SOCK_STREAM
        )

        if not addresses:
            return False

        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                return False

        return True
    except (ValueError, OSError):
        return False


@app.route("/", methods=["GET"])
@limiter.limit("30 per minute")
def home():
    return render_template_string(HTML)


@app.route("/download", methods=["POST"])
@limiter.limit("3 per minute")
def download():
    url = request.form.get("url", "").strip()

    if len(url) > 2048 or not valid_url(url):
        return "Enlace HTTPS no válido o no permitido.", 400

    folder = tempfile.mkdtemp(prefix="video_")

    try:
        command = [
            "yt-dlp",
            "--no-playlist",
            "--max-filesize", "100M",
            "--socket-timeout", "15",
            "--retries", "1",
            "--no-warnings",
            "-f", "best",
            "-o", os.path.join(folder, "video.%(ext)s"),
            url
        ]

        subprocess.run(
            command,
            capture_output=True,
            timeout=120,
            check=True
        )

        files = [
            path for path in glob.glob(os.path.join(folder, "video.*"))
            if os.path.isfile(path)
        ]

        if not files:
            shutil.rmtree(folder, ignore_errors=True)
            return "No se encontró el archivo descargado.", 404

        path = files[0]
        response = send_file(
            path,
            as_attachment=True,
            download_name=os.path.basename(path)
        )
        response.call_on_close(
            lambda: shutil.rmtree(folder, ignore_errors=True)
        )
        return response

    except subprocess.TimeoutExpired:
        shutil.rmtree(folder, ignore_errors=True)
        return "La descarga tardó demasiado. Inténtalo de nuevo.", 408

    except subprocess.CalledProcessError:
        shutil.rmtree(folder, ignore_errors=True)
        return (
            "No se pudo descargar. El sitio puede no ser compatible, "
            "el archivo superar el límite o requerir autorización."
        ), 400

    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        app.logger.exception("Error procesando la descarga")
        return "Error al procesar el vídeo.", 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
