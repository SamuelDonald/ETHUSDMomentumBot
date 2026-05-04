"""
signal_server.py  —  Drop-in replacement for ZMQSignalSender
Runs a lightweight HTTP server. MT5 EA polls it via WebRequest.
No DLLs, no ZeroMQ, no port binding issues.

Usage:
    pip install flask
    Run alongside main.py — it starts automatically when imported.

Place this file at:
    ETHUSDMomentumBot/eth_scalper_engine/bridge/signal_server.py
"""

import json
import logging
import threading
from collections import deque
from datetime import datetime

from flask import Flask, jsonify, request

logger = logging.getLogger("eth_scalper")

app = Flask(__name__)

# Thread-safe signal queue — holds the latest signal only
# MT5 polls this endpoint and consumes the signal
_signal_store: dict = {}
_lock = threading.Lock()
_delivered_ids: deque = deque(maxlen=100)   # prevent duplicate delivery


@app.route("/signal", methods=["GET"])
def get_signal():
    """MT5 EA polls this endpoint every 100ms via WebRequest."""
    with _lock:
        if not _signal_store:
            return jsonify({"signal": None}), 200

        sig = dict(_signal_store)
        sig_id = sig.get("timestamp", 0)

        # Mark as delivered — MT5 receives it once only
        if sig_id in _delivered_ids:
            return jsonify({"signal": None}), 200

        _delivered_ids.append(sig_id)
        return jsonify(sig), 200


@app.route("/status", methods=["GET"])
def status():
    """Health check — MT5 can ping this to confirm server is alive."""
    return jsonify({
        "status": "running",
        "time": datetime.utcnow().isoformat(),
        "has_signal": bool(_signal_store),
    }), 200


@app.route("/push", methods=["POST"])
def push_signal():
    """Internal endpoint — Python engine posts signals here."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "empty payload"}), 400
    with _lock:
        _signal_store.clear()
        _signal_store.update(data)
    logger.info("Signal queued for MT5: %s", data.get("signal"))
    return jsonify({"ok": True}), 200


class HTTPSignalSender:
    """
    Drop-in replacement for ZMQSignalSender.
    Same interface: send(signal_dict) and close().
    Posts signals to the local Flask server.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 5558):
        self.url = f"http://{host}:{port}/push"
        self._start_server(host, port)

    def _start_server(self, host: str, port: int) -> None:
        """Start Flask in a background daemon thread."""
        def run():
            import logging as _log
            _log.getLogger("werkzeug").setLevel(_log.ERROR)   # silence Flask request logs
            app.run(host=host, port=port, debug=False, use_reloader=False)

        t = threading.Thread(target=run, daemon=True)
        t.start()
        logger.info("HTTP signal server started on http://%s:%d", host, port)

    def send(self, signal: dict) -> bool:
        try:
            import urllib.request
            body = json.dumps(signal).encode()
            req = urllib.request.Request(
                self.url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=1) as resp:
                return resp.status == 200
        except Exception as e:
            logger.warning("HTTP signal send failed: %s", e)
            return False

    def close(self) -> None:
        # Flask daemon thread exits automatically when main process ends
        logger.info("HTTP signal server shutting down")
