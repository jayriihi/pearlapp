"""Standalone wind map and observation endpoint; dashboard routes stay isolated."""
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from flask import Blueprint, current_app, jsonify, render_template, send_file

from app.wind_map_config import PEARL_STATION
from app.wind_map_observation import observations, POLL_SECONDS, STALE_SECONDS

wind_map_bp = Blueprint("wind_map", __name__)


@wind_map_bp.get("/wind-map")
def page():
    return render_template("wind_map.html", station=PEARL_STATION,
                           poll_seconds=POLL_SECONDS, stale_seconds=STALE_SECONDS)


@wind_map_bp.get("/wind-map/observation")
def observation():
    payload = observations.get()
    response = jsonify(payload)
    response.status_code = 503 if payload["status"] == "unavailable" else 200
    response.headers["Cache-Control"] = "no-store"
    if response.status_code == 503:
        response.headers["Retry-After"] = str(POLL_SECONDS)
    return response


@wind_map_bp.get("/wind-map/geography")
def geography():
    """Offer the entire derived geography database and its ODbL notices."""
    folder = Path(current_app.static_folder) / "wind-map" / "data"
    archive = BytesIO()
    names = ("land.geojson", "roads.geojson", "context.geojson", "labels.geojson",
             "metadata.json", "LICENSE.txt", "README.txt")
    with ZipFile(archive, "w", ZIP_DEFLATED) as zipped:
        for name in names:
            zipped.write(folder / name, name)
    archive.seek(0)
    return send_file(archive, mimetype="application/zip", as_attachment=True,
                     download_name="pearl-bermuda-geography.zip", max_age=3600)
