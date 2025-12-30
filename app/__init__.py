import os

from flask import Flask, make_response, render_template, request

app = Flask(__name__)
app.secret_key = "riihiluoma"

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
