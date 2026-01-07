import logging
from app import app

app.debug = False
logging.getLogger("werkzeug").setLevel(logging.ERROR)
app.logger.disabled = True
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
    
#(debug=True)
#(host="0.0.0.0")
