import re
from dataclasses import dataclass
from typing import Dict


ETHUSD_REGEX = re.compile(r"^ETHUSD[a-zA-Z0-9._#-]*$")


@dataclass
class SymbolMapper:
    canonical_symbol: str
    broker_symbol_map: Dict[str, str]

    def normalize_symbol(self, symbol: str) -> str:
        if not symbol:
            return self.canonical_symbol

        normalized = symbol.upper()
        if normalized.startswith(self.canonical_symbol):
            return self.canonical_symbol

        if ETHUSD_REGEX.match(normalized):
            return self.canonical_symbol

        return normalized

    def is_ethusd_family(self, symbol: str) -> bool:
        if not symbol:
            return False
        check = symbol.upper()
        return check.startswith(self.canonical_symbol) or bool(ETHUSD_REGEX.match(check))

    def map_for_broker(self, broker_name: str) -> str:
        key = (broker_name or "").upper()
        return self.broker_symbol_map.get(key, self.broker_symbol_map.get("DEFAULT", self.canonical_symbol))
