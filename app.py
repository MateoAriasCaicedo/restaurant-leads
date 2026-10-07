"""Run the web app.

Usage: python app.py [--no-browser]
Serves the UI and API on http://127.0.0.1:<config.UI_PORT> (this machine only). Build the UI once with
`npm --prefix ui install && npm --prefix ui run build`.
"""
import sys
import threading
import webbrowser

import uvicorn

from leadgen import config

if __name__ == "__main__":
    url = f"http://127.0.0.1:{config.UI_PORT}"
    print(f"Restaurant leads: {url}   (Ctrl+C to stop)")
    if "--no-browser" not in sys.argv:
        threading.Timer(1.2, webbrowser.open, [url]).start()
    uvicorn.run("server.app:app", host="127.0.0.1", port=config.UI_PORT, log_level="warning")
