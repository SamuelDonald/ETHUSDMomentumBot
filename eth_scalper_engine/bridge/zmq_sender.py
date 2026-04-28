import json
from typing import Any, Dict

import zmq


class ZMQSignalSender:
    def __init__(self, endpoint: str, high_water_mark: int = 1000):
        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.PUSH)
        self.socket.setsockopt(zmq.SNDHWM, high_water_mark)
        self.socket.connect(endpoint)

    def send(self, signal: Dict[str, Any]) -> bool:
        required_fields = {"symbol", "normalized_symbol", "signal", "entry", "sl", "tp", "timestamp"}
        if not signal or not required_fields.issubset(signal.keys()):
            return False

        try:
            self.socket.send_string(json.dumps(signal), flags=zmq.NOBLOCK)
            return True
        except zmq.Again:
            return False

    def close(self) -> None:
        self.socket.close(0)
