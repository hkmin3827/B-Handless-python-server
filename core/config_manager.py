import json
import uuid
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config.json"


class ConfigManager:
    def load(self) -> dict:
        if not CONFIG_PATH.exists():
            default = self._default()
            self.save(default)
            return default
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, config: dict):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def get_items(self) -> list:
        return self.load().get("startup_items", [])

    def get_item(self, item_id: str) -> dict | None:
        return next((i for i in self.get_items() if i["id"] == item_id), None)

    def add_item(self, item: dict) -> dict:
        config = self.load()
        item["id"] = str(uuid.uuid4())[:8]
        item.setdefault("enabled", True)
        item.setdefault("delay_seconds", 0)
        config["startup_items"].append(item)
        self.save(config)
        return item

    def update_item(self, item_id: str, updates: dict) -> dict | None:
        config = self.load()
        for i, item in enumerate(config["startup_items"]):
            if item["id"] == item_id:
                config["startup_items"][i].update(updates)
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
