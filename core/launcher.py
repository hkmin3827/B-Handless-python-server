import logging
import os
import subprocess
import threading
import time
import webbrowser
from pathlib import Path

LOGS_DIR = Path(__file__).parent.parent / "logs"
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

_EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def _find_edge() -> str | None:
    return next((p for p in _EDGE_PATHS if os.path.exists(p)), None)


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
    url = item.get("url", "")
    if not url:
        log.error(f"[browser_url] {label}: url이 비어 있습니다.")
        return

    browser = item.get("browser", "edge")
    if browser == "edge":
        edge = _find_edge()
        if edge:
            subprocess.Popen([edge, url])
            log.info(f"[browser_url] {label} → Edge: {url}")
            return
        log.warning(f"[browser_url] {label}: Edge를 찾지 못해 기본 브라우저로 오픈합니다.")

    webbrowser.open(url)
    log.info(f"[browser_url] {label} → 기본 브라우저: {url}")


def _launch_executable(item: dict, label: str):
    path = item.get("path", "")
    if not path:
        log.error(f"[exe] {label}: path가 비어 있습니다.")
        return

    # 상대 경로면 프로젝트 루트 기준으로 해석
    resolved = Path(path) if Path(path).is_absolute() else Path(__file__).parent.parent / path

    if not resolved.exists():
        log.error(f"[exe] {label}: 파일 없음 → {resolved}")
        return

    args = item.get("args", [])
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
