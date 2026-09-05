"""
Authentifizierung:
- Menschlicher Login (Benutzername/Passwort) -> zeitlich begrenztes signiertes Token
- Geraete-Token (fest, aus .env) fuer PC-Client und WoL-Relay
"""
from functools import wraps

from flask import request, jsonify, current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import check_password_hash


def create_login_token(username: str) -> str:
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return s.dumps({"user": username})


def verify_login_token(token: str) -> bool:
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        s.loads(token, max_age=current_app.config["TOKEN_MAX_AGE"])
        return True
    except (BadSignature, SignatureExpired):
        return False


def check_credentials(username: str, password: str) -> bool:
    cfg = current_app.config
    if username != cfg["AUTH_USERNAME"]:
        return False
    return check_password_hash(cfg["AUTH_PASSWORD_HASH"], password)


def _extract_bearer():
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[len("Bearer "):].strip()
    return None


def require_login(fn):
    """Schuetzt Endpunkte, die vom Handy/Browser (Mensch) aufgerufen werden."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_bearer()
        if not token or not verify_login_token(token):
            return jsonify({"error": "Nicht angemeldet oder Sitzung abgelaufen."}), 401
        return fn(*args, **kwargs)

    return wrapper


def require_device(fn):
    """Schuetzt Endpunkte, die nur der PC-Client / Relay aufrufen duerfen."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_bearer()
        if not token or token != current_app.config["DEVICE_TOKEN"]:
            return jsonify({"error": "Ungueltiges Geraete-Token."}), 401
        return fn(*args, **kwargs)

    return wrapper
