"""Application privée de démonstration pour les essais réseau SUP'COM–6NLG."""

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from uuid import uuid4

from flask import Flask, g, jsonify, render_template, request


MAX_REQUEST_BYTES = 1024 * 1024  # 1 Mio, corps HTTP complet compris
MAX_TEXT_CHARS = 10_000
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

logger = logging.getLogger("ztna_demo")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES

    @app.before_request
    def assign_request_id():
        supplied = request.headers.get("X-Request-ID", "")
        g.request_id = supplied if REQUEST_ID_PATTERN.fullmatch(supplied) else uuid4().hex

    @app.after_request
    def add_headers_and_log(response):
        response.headers["X-Request-ID"] = g.request_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        # remote_addr est le pair de la connexion. Les trois en-têtes ci-dessous
        # sont seulement des valeurs observées : un client peut les fabriquer.
        logger.info(json.dumps({
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "request_id": g.request_id,
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "network_peer": request.remote_addr,
            "observed_host": request.headers.get("Host"),
            "observed_x_forwarded_for": request.headers.get("X-Forwarded-For"),
            "observed_x_forwarded_proto": request.headers.get("X-Forwarded-Proto"),
        }, ensure_ascii=False))
        return response

    @app.errorhandler(413)
    def request_too_large(_error):
        return render_template("result.html", title="Requête trop volumineuse",
                               message="La requête dépasse la limite de 1 Mio."), 413

    @app.get("/")
    def home():
        return render_template("home.html")

    @app.get("/portal")
    def portal():
        return render_template("portal.html")

    @app.get("/admin")
    def admin():
        return render_template("admin.html")

    @app.get("/upload")
    def upload():
        return render_template("upload.html")

    @app.post("/upload/file")
    def upload_file():
        uploaded = request.files.get("file")
        if uploaded is None or not uploaded.filename:
            return render_template("result.html", title="Fichier absent",
                                   message="Aucun fichier de test n'a été reçu."), 400

        # Le fichier reste en mémoire pendant cette requête ; rien n'est sauvegardé.
        size = len(uploaded.read())
        return render_template("result.html", title="Fichier reçu",
                               message="La requête POST est arrivée à Flask.",
                               details={"Nom déclaré": uploaded.filename,
                                        "Taille reçue": f"{size} octets",
                                        "Type déclaré": uploaded.content_type or "non indiqué"})

    @app.post("/upload/text")
    def upload_text():
        submitted = request.form.get("text", "")
        if len(submitted) > MAX_TEXT_CHARS:
            return render_template("result.html", title="Texte trop long",
                                   message="Le texte dépasse 10 000 caractères."), 413
        return render_template("result.html", title="Texte reçu",
                               message="La requête POST est arrivée à Flask. Le contenu n'est ni affiché ni conservé.",
                               details={"Longueur reçue": f"{len(submitted)} caractères"})

    @app.get("/observations")
    def observations():
        return render_template("observations.html", observations={
            "Méthode": request.method,
            "Chemin": request.path,
            "Adresse du pair réseau": request.remote_addr or "non disponible",
            "Host observé": request.headers.get("Host", "non fourni"),
            "X-Forwarded-For observé": request.headers.get("X-Forwarded-For", "non fourni"),
            "X-Forwarded-Proto observé": request.headers.get("X-Forwarded-Proto", "non fourni"),
        })

    @app.get("/health")
    def health():
        return jsonify(status="ok", request_id=g.request_id)

    return app


app = create_app()


if __name__ == "__main__":
    cert_file = os.environ.get("TLS_CERT_FILE")
    key_file = os.environ.get("TLS_KEY_FILE")
    if bool(cert_file) != bool(key_file):
        raise SystemExit("TLS_CERT_FILE et TLS_KEY_FILE doivent être définis ensemble.")
    app.run(host=os.environ.get("APP_HOST", "127.0.0.1"),
            port=int(os.environ.get("APP_PORT", "5000")),
            ssl_context=(cert_file, key_file) if cert_file else None,
            debug=False, use_reloader=False)
