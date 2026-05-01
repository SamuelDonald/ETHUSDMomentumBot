import json
import logging
from typing import Any, Dict

import zmq


class ZMQSignalSender:
    def __init__(self, endpoint: str, high_water_mark: int = 1000):
        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.PUSH)
        self.socket.setsockopt(zmq.SNDHWM, high_water_mark)
        self.socket.connect(endpoint)
        self.logger = logging.getLogger(__name__)

    def send(self, signal: Dict[str, Any]) -> bool:
        required_fields = {"symbol", "normalized_symbol", "signal", "entry", "sl", "tp", "timestamp"}
        if not signal or not required_fields.issubset(signal.keys()):
            return False

        try:
            self.socket.send_string(json.dumps(signal), flags=zmq.NOBLOCK)
            return True
        except zmq.Again:
            self.logger.warning("ZMQ send failed; persisting signal to dead-letter log")
            self._persist_dead_letter(signal)
            return False

    def _persist_dead_letter(self, signal: Dict[str, Any]) -> None:
        try:
            with open("failed_signals.ndjson", "a", encoding="utf-8") as handle:
                handle.write(json.dumps(signal) + "\n")
        except OSError:
            self.logger.exception("Unable to persist failed signal")

    def close(self) -> None:
        self.socket.close(0)
