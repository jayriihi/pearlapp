import logging
from app import app

app.debug = True
logging.getLogger("werkzeug").setLevel(logging.INFO)
app.logger.disabled = False
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
    
#(debug=True)
#(host="0.0.0.0")
