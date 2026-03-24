import logging
import os

from app import app

logging.getLogger("werkzeug").setLevel(logging.INFO)
app.logger.disabled = False


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "1").lower() in {"1", "true", "yes", "on"}
    port = 5001
    app.run(host="0.0.0.0", port=port, debug=debug)
