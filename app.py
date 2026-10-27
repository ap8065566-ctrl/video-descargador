
from flask import Flask, request, render_template_string, jsonify
from urllib.parse import urlparse
import os
import re
import subprocess

app = Flask(__name__)

HTML = """
<!doctype html>
<html lang="es">
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta charset="utf-8">
<title>Mi descargador de vídeos</title>
<style>
body { font-family: Arial, sans-serif; background:#101827;
color:white; margin:0; padding:24px; }
main { max-width:520px; margin:50px auto; text-align:center; }
input,button { box-sizing:border-box; width:100%; padding:15px;
margin-top:12px; border-radius:10px; font-size:16px; }
input { border:1px solid #526078; background:#202c40; color:white; }
button { background:#3675f5; color:white; border:0; font-weight:bold; }
p { color:#b8c4d8; line-height:1.5; }
</style>
</head>
<body><main>
<h1>Descargador de vídeos</h1>
<p>Pega el enlace de un vídeo que tengas permiso para descargar.</p>
<form method="post" action="/info">
<input name="url" type="url" placeholder="https://..." required>
<button type="submit">Analizar vídeo</button>
</form>
<div id="resultado"></div>
<p>Los enlaces protegidos o no compatibles pueden fallar.</p>
</main></body></html>
"""

@app.route("/", methods=["GET"])
def home():
    return render_template_string(HTML)

@app.route("/info", methods=["POST"])
def info():
    url = request.form.get("url", "").strip()
    parsed = urlparse(url)

    if parsed.scheme != "https" or not parsed.hostname:
        return "Introduce un enlace HTTPS válido.", 400

    host = parsed.hostname.lower().rstrip(".")
    if not re.fullmatch(r"[a-z0-9.-]+", host):
        return "Dominio no válido.", 400

    try:
        result = subprocess.run(
            ["yt-dlp", "--no-playlist", "--simulate",
             "--print", "%(title)s", url],
            capture_output=True, text=True, timeout=25
        )
        if result.returncode != 0:
            return ("No se pudo analizar el vídeo. Puede no ser "
                    "compatible o requerir autorización."), 400

        title = result.stdout.strip()[:300]
        return ("Vídeo compatible: " + title +
                ". La descarga se añadirá en el siguiente paso.")
    except subprocess.TimeoutExpired:
        return "El análisis tardó demasiado. Inténtalo de nuevo.", 408
    except Exception:
        return "No se pudo procesar el enlace.", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
