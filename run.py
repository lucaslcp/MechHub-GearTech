"""Inicia o MechHub localmente: python run.py  →  http://127.0.0.1:5000"""
import os

from mechhub import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=os.environ.get("MECHHUB_DEBUG") == "1")
