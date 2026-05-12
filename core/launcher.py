import logging
import subprocess
import sys
import threading
import time
import webbrowser
import winreg
from pathlib import Path

from core.security import SUPPORTED_BROWSERS, validate_exe_path, validate_url


def _app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


LOGS_DIR = _app_root() / "logs"
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "startup.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("b-handless")

_APP_PATHS_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"


def _find_browser(browser: str) -> str | None:
    """레지스트리 App Paths에서 브라우저 실행 파일 경로 반환. 없으면 None."""
    exe = SUPPORTED_BROWSERS.get(browser.lower())
    if not exe:
        return None
    key_path = f"{_APP_PATHS_KEY}\\{exe}"
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            key = winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ)
            path, _ = winreg.QueryValueEx(key, "")
            winreg.CloseKey(key)
            return path
        except (FileNotFoundError, OSError):
            continue
    return None


def launch_item(item: dict):
    label = item.get("label", item.get("id", "?"))
    item_type = item.get("type", "")

    if item_type == "browser_url":
        _launch_browser_url(item, label)

    elif item_type in ("exe", "app"):
        _launch_executable(item, label)

    elif item_type == "uploaded_exe":
        # uploads/ 디렉토리 안의 .exe 실행
        # path 필드에 uploads/폴더명/파일.exe 형태로 저장
        _launch_executable(item, label)

    else:
        log.warning(f"알 수 없는 타입: '{item_type}' ({label})")


def _launch_browser_url(item: dict, label: str):
    try:
        url = validate_url(item.get("url", ""))
    except ValueError as e:
        log.error(f"[browser_url] {label}: {e}")
        return

    browser = item.get("browser", "edge").lower()
    browser_path = _find_browser(browser)

    if browser_path:
        subprocess.Popen([browser_path, url])
        log.info(f"[browser_url] {label} → {browser}: {url}")
    else:
        log.warning(
            f"[browser_url] {label}: '{browser}'을(를) 설치 확인 불가 — "
            "해당 브라우저가 PC에 설치되어 있어야 합니다. 기본 브라우저로 대신 오픈합니다."
        )
        webbrowser.open(url)
        log.info(f"[browser_url] {label} → 기본 브라우저(폴백): {url}")


def _launch_executable(item: dict, label: str):
    try:
        resolved = validate_exe_path(item.get("path", ""))
    except ValueError as e:
        log.error(f"[exe] {label}: {e}")
        return

    if not resolved.exists():
        log.error(f"[exe] {label}: 파일 없음 → {resolved}")
        return

    args = item.get("args", [])
    if not isinstance(args, list):
        log.error(f"[exe] {label}: args는 리스트여야 합니다.")
        return

    subprocess.Popen([str(resolved)] + args)
    log.info(f"[exe] {label} → {resolved}")


def _run_with_delay(item: dict):
    """각 항목을 delay_seconds 뒤에 실행 (스레드에서 호출)"""
    delay = item.get("delay_seconds", 0)
    if delay > 0:
        time.sleep(delay)
    try:
        launch_item(item)
    except Exception as e:
        label = item.get("label", item.get("id", "?"))
        log.error(f"[ERROR] {label}: {e}")


def launch_all(config: dict):
    items = config.get("startup_items", [])
    enabled = [i for i in items if i.get("enabled", True)]

    if not enabled:
        log.info("실행할 항목이 없습니다. config.json을 확인하세요.")
        return

    log.info(f"=== B-Handless 시작 — {len(enabled)}개 항목 ===")

    # 각 항목을 독립 스레드에서 실행 → delay가 각자 독립적으로 동작
    threads = [
        threading.Thread(target=_run_with_delay, args=(item,), daemon=False)
        for item in enabled
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()  # 가장 긴 delay + 실행까지 기다린 후 프로세스 종료

    log.info("=== B-Handless 실행 완료 ===")


def launch_by_id(config: dict, item_id: str) -> bool:
    """대시보드 '지금 바로 실행' 버튼용"""
    item = next((i for i in config.get("startup_items", []) if i["id"] == item_id), None)
    if item is None:
        log.error(f"항목을 찾을 수 없습니다: {item_id}")
        return False
    try:
        launch_item(item)
        return True
    except Exception as e:
        log.error(f"[ERROR] {item.get('label', item_id)}: {e}")
        return False
