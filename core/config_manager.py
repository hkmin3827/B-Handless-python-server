import hashlib
import json
import sys
import uuid
from pathlib import Path

from core.security import validate_item


def _app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


CONFIG_PATH = _app_root() / "config.json"
_HASH_PATH = CONFIG_PATH.with_suffix(".json.hash")


class ConfigManager:
    def load(self) -> dict:
        if not CONFIG_PATH.exists():
            default = self._default()
            self.save(default)
            return default

        raw = CONFIG_PATH.read_bytes()
        self._verify_hash(raw)

        return json.loads(raw.decode("utf-8"))

    def save(self, config: dict):
        content = json.dumps(config, ensure_ascii=False, indent=2)
        raw = content.encode("utf-8")
        CONFIG_PATH.write_bytes(raw)
        _HASH_PATH.write_text(self._sha256(raw), encoding="utf-8")

    def _sha256(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _verify_hash(self, raw: bytes):
        """해시 파일이 있을 때만 검증. 불일치 시 경고만 출력 (실행은 계속)."""
        if not _HASH_PATH.exists():
            return
        expected = _HASH_PATH.read_text(encoding="utf-8").strip()
        actual = self._sha256(raw)
        if expected != actual:
            import logging
            logging.getLogger("b-handless").warning(
                "⚠️  config.json 해시 불일치 — 파일이 외부에서 변조됐을 수 있습니다."
            )

    def get_items(self) -> list:
        return self.load().get("startup_items", [])

    def get_item(self, item_id: str) -> dict | None:
        return next((i for i in self.get_items() if i["id"] == item_id), None)

    def add_item(self, item: dict) -> dict:
        item.setdefault("enabled", True)
        item.setdefault("delay_seconds", 0)
        validate_item(item)  # 저장 전 검증
        config = self.load()
        item["id"] = str(uuid.uuid4())[:8]
        config["startup_items"].append(item)
        self.save(config)
        return item

    def update_item(self, item_id: str, updates: dict) -> dict | None:
        config = self.load()
        for i, item in enumerate(config["startup_items"]):
            if item["id"] == item_id:
                merged = {**item, **updates}
                validate_item(merged)  # 저장 전 검증
                config["startup_items"][i] = merged
                self.save(config)
                return config["startup_items"][i]
        return None

    def toggle_item(self, item_id: str) -> dict | None:
        item = self.get_item(item_id)
        if item is None:
            return None
        return self.update_item(item_id, {"enabled": not item.get("enabled", True)})

    def delete_item(self, item_id: str) -> bool:
        config = self.load()
        before = len(config["startup_items"])
        config["startup_items"] = [
            i for i in config["startup_items"] if i["id"] != item_id
        ]
        if len(config["startup_items"]) < before:
            self.save(config)
            return True
        return False

    def get_settings(self) -> dict:
        return self.load().get("settings", {})

    def update_settings(self, updates: dict):
        config = self.load()
        config["settings"].update(updates)
        self.save(config)

    def _default(self) -> dict:
        return {
            "startup_items": [],
            "settings": {
                "api_port": 8000,
                "dashboard_port": 3000,
                "log_enabled": True,
                "registered_as_startup": False,
            },
        }
