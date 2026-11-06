
import os
import glob
import socket
import shutil
import tempfile
import subprocess
import ipaddress
from urllib.parse import urlparse

from flask import (
    Flask, request, render_template_string, send_file
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

MAX_FILE_SIZE = "1G"
DOWNLOAD_TIMEOUT = 600

HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#100b1c">
<title>VideoDescarga | Descarga tus vídeos</title>
<meta name="description" content="VideoDescarga: herramienta para descargar contenido autorizado de sitios compatibles.">

<style>
* { box-sizing: border-box; }

body {
    margin: 0;
    min-height: 100vh;
    font-family: Arial, Helvetica, sans-serif;
    color: #ffffff;
    background:
        radial-gradient(ellipse at top, #352052 0%, transparent 45%),
        linear-gradient(145deg, #0b0812, #171020 55%, #09070e);
}

header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 22px 7%;
    border-bottom: 1px solid rgba(255,255,255,.08);
}

.logo {
    font-size: 23px;
    font-weight: 800;
    letter-spacing: -.8px;
}

.logo span { color: #b56aff; }

.tag {
    color: #c8b6df;
    font-size: 12px;
}

main {
    width: 92%;
    max-width: 720px;
    margin: 65px auto;
    text-align: center;
}

.label {
    display: inline-block;
    padding: 9px 16px;
    border: 1px solid #7541a5;
    border-radius: 30px;
    color: #d7b5ff;
    background: rgba(153, 80, 220, .10);
    font-size: 12px;
    letter-spacing: 1px;
}

h1 {
    margin: 25px 0 12px;
    font-size: clamp(34px, 7vw, 54px);
    line-height: 1.12;
}

h1 span { color: #c17aff; }

.subtitle {
    max-width: 540px;
    margin: 0 auto;
    color: #bdb2ca;
    line-height: 1.7;
    font-size: 15px;
}

.download-card {
    margin-top: 38px;
    padding: 30px;
    border: 1px solid rgba(194, 125, 255, .25);
    border-radius: 22px;
    background: rgba(31, 22, 43, .88);
    box-shadow: 0 15px 55px rgba(0,0,0,.35);
}

input {
    width: 100%;
    padding: 18px;
    border: 1px solid #59466c;
    border-radius: 12px;
    outline: none;
    background: #100b19;
    color: white;
    font-size: 15px;
}

input:focus {
    border-color: #bd76ff;
    box-shadow: 0 0 0 3px rgba(189,118,255,.12);
}

button {
    width: 100%;
    margin-top: 15px;
    padding: 17px;
    border: none;
    border-radius: 12px;
    color: white;
    background: linear-gradient(100deg, #8539d7, #bd65ff);
    font-size: 16px;
    font-weight: bold;
    cursor: pointer;
}

button:hover { filter: brightness(1.12); }

.hint {
    margin: 15px 0 0;
    color: #a99bb9;
    font-size: 12px;
    line-height: 1.6;
}

.ad-box {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 95px;
    margin: 28px 0;
    padding: 15px;
    border: 1px dashed #574369;
    border-radius: 13px;
    color: #88799a;
    background: rgba(255,255,255,.025);
    font-size: 12px;
    letter-spacing: 1px;
}

.features {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    margin-top: 35px;
}

.feature {
    padding: 20px 10px;
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 14px;
    background: rgba(255,255,255,.035);
}

.feature .icon { font-size: 25px; }

.feature h3 {
    margin: 12px 0 7px;
    font-size: 14px;
}

.feature p {
    margin: 0;
    color: #a99bb9;
    font-size: 12px;
    line-height: 1.5;
}

section.info {
    margin-top: 50px;
    text-align: left;
}

.info h2 { font-size: 21px; }

.info p {
    color: #bdb2ca;
    font-size: 14px;
    line-height: 1.8;
}

footer {
    margin-top: 65px;
    padding: 28px 15px;
    border-top: 1px solid rgba(255,255,255,.08);
    color: #998ba8;
    text-align: center;
    font-size: 12px;
    line-height: 1.8;
}

.notice {
    margin-top: 20px;
    padding: 15px;
    border-radius: 12px;
    background: rgba(189,118,255,.09);
    color: #d8c4ed;
    font-size: 13px;
    line-height: 1.6;
}

@media (max-width: 520px) {
    header { padding: 19px 5%; }
    main { margin: 42px auto; }
    .download-card { padding: 20px 15px; }
    .features { grid-template-columns: 1fr; }
    .feature { padding: 18px; }
}
</style>
</head>

<body>
<header>
    <div class="logo">Video<span>Descarga</span></div>
    <div class="tag">DESCARGAS ONLINE</div>
</header>

<main>
    <div class="label">TU HERRAMIENTA DE VÍDEOS</div>

    <h1>Descarga tus vídeos <span>fácilmente</span></h1>

    <p class="subtitle">
        Pega el enlace de un vídeo de un sitio compatible
        y descarga el contenido cuando tengas autorización.
    </p>

    <div class="ad-box">ESPACIO PUBLICITARIO</div>

    <div class="download-card">
        <form method="post" action="/download">
            <input
                name="url"
                type="url"
                placeholder="Pega aquí el enlace del vídeo..."
                maxlength="2048"
                required
            >
            <button type="submit">↓ DESCARGAR VÍDEO</button>
        </form>

        <p class="hint">
            Tamaño máximo: 1 GB.
            Sujeto a los recursos del servidor y a la compatibilidad del sitio.
        </p>
    </div>

    <div class="features">
        <div class="feature">
            <div class="icon">⚡</div>
            <h3>Sencillo</h3>
            <p>Pega un enlace y comienza.</p>
        </div>

        <div class="feature">
            <div class="icon">📱</div>
            <h3>Multidispositivo</h3>
            <p>Diseñado para móviles y ordenadores.</p>
        </div>

        <div class="feature">
            <div class="icon">🔒</div>
            <h3>Protección</h3>
            <p>Validación de enlaces y límites de uso.</p>
        </div>
    </div>

    <div class="ad-box">ESPACIO PUBLICITARIO</div>

    <section class="info">
        <h2>¿Cómo funciona?</h2>
        <p>1. Copia el enlace del contenido que tienes derecho a descargar.</p>
        <p>2. Pégalo en el campo de descarga.</p>
        <p>3. Pulsa el botón y espera a que termine el procesamiento.</p>
    </section>

    <div class="notice">
        Utiliza VideoDescarga únicamente para contenido propio,
        de dominio público o cuyo titular te haya autorizado.
        No eludas restricciones técnicas ni medidas de protección.
    </div>
</main>

<footer>
    <strong>VideoDescarga</strong><br>
    Herramienta de descarga para contenido autorizado.<br>
    © 2026 VideoDescarga
</footer>
</body>
</html>
"""

MESSAGE_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VideoDescarga</title>
<style>
body {
    background: #100b19;
    color: white;
    font-family: Arial, sans-serif;
    text-align: center;
    padding: 60px 20px;
}
.card {
    max-width: 480px;
    margin: auto;
    padding: 30px;
    border: 1px solid #7541a5;
    border-radius: 20px;
    background: #21172e;
}
h1 { color: #c17aff; }
p { color: #cbbbdc; line-height: 1.7; }
a {
    display: inline-block;
    margin-top: 20px;
    padding: 14px 24px;
    border-radius: 10px;
    color: white;
    background: #953fdf;
    text-decoration: none;
}
</style>
</head>
<body>
<div class="card">
    <h1>VideoDescarga</h1>
    <p>{{ message }}</p>
    <a href="/">Volver al inicio</a>
</div>
</body>
</html>
"""


def show_message(message, status=200):
    return render_template_string(
        MESSAGE_HTML,
        message=message
    ), status


def valid_url(url):
    try:
        parsed = urlparse(url)
        host = parsed.hostname

        if parsed.scheme != "https" or not host:
            return False

        if parsed.username or parsed.password:
            return False

        if parsed.port not in (None, 443):
            return False

        if host == "localhost" or host.endswith(".localhost"):
            return False

        addresses = socket.getaddrinfo(
            host,
            443,
            type=socket.SOCK_STREAM
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
        return show_message(
            "El enlace HTTPS no es válido o no está permitido.",
            400
        )

    folder = tempfile.mkdtemp(prefix="video_")

    try:
        command = [
            "yt-dlp",
            "--ignore-config",
            "--no-playlist",
            "--max-filesize", MAX_FILE_SIZE,
            "--socket-timeout", "30",
            "--retries", "3",
            "--fragment-retries", "3",
            "--no-warnings",
            "-f", "best",
            "-o", os.path.join(folder, "video.%(ext)s"),
            url
        ]

        subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=DOWNLOAD_TIMEOUT,
            check=True
        )

        files = [
            path for path in glob.glob(
                os.path.join(folder, "video.*")
            )
            if os.path.isfile(path)
        ]

        if not files:
            shutil.rmtree(folder, ignore_errors=True)
            return show_message(
                "No se encontró ningún archivo descargable.",
                404
            )

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
        return show_message(
            "La descarga tardó demasiado. El servidor puede no soportar "
            "archivos tan grandes. Inténtalo de nuevo.",
            408
        )

    except subprocess.CalledProcessError as error:
        app.logger.error(
            "yt-dlp error: %s",
            (error.stderr or "")[-3000:]
        )
        shutil.rmtree(folder, ignore_errors=True)
        return show_message(
            "No se pudo descargar. Comprueba que el sitio sea compatible "
            "y que tengas autorización para descargar el contenido.",
            400
        )

    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        app.logger.exception("Error procesando la descarga")
        return show_message(
            "Se produjo un error al procesar el vídeo.",
            500
        )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
