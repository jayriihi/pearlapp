import os
import warnings

from flask import Flask, make_response, render_template, request

app = Flask(__name__)
APP_ENV = os.environ.get("APP_ENV", "development").lower()
secret_key = os.environ.get("SECRET_KEY")
if not secret_key:
    if APP_ENV in {"staging", "production"}:
        raise RuntimeError(
            "SECRET_KEY environment variable must be set when APP_ENV is staging or production"
        )
    secret_key = "local-dev-secret-key-change-me"
    warnings.warn(
        "SECRET_KEY is not set; using the local development fallback.",
        stacklevel=2,
    )

app.config["SECRET_KEY"] = secret_key
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get(
    "SESSION_COOKIE_SECURE",
    "",
).lower() in {"1", "true", "yes", "on"}

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MAINTENANCE_FLAG = os.path.join(BASE_DIR, "maintenance.on")


@app.before_request
def maintenance_mode():
    if not os.path.exists(MAINTENANCE_FLAG):
        return None

    if request.path.startswith("/static/"):
        return None

    bypass_key = os.environ.get("MAINT_BYPASS_KEY", "")
    if bypass_key and request.args.get("bypass") == bypass_key:
        return None

    response = make_response(render_template("maintenance.html"), 503)
    response.headers["Retry-After"] = "300"
    return response

from app import views
