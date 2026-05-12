"""
  python main.py              → 트레이 앱 실행 (서버 + 시작 항목 + 트레이 아이콘)
  python main.py --serve      → FastAPI 서버 실행 (대시보드 연동용)
  python main.py --register   → Windows 시작 프로그램에 등록
  python main.py --unregister → Windows 시작 프로그램에서 제거
  python main.py --status     → 등록 상태 확인
"""

import sys
import traceback
from core.config_manager import ConfigManager
from core.launcher import launch_all, LOGS_DIR
from core import scheduler
from core.security import SERVER_HOST


def _run_uvicorn(app, host: str, port: int):
    """uvicorn 실행 — console=False 환경에서 log_config=None 필수 (stdout=None 충돌 방지)"""
    try:
        import uvicorn
        uvicorn.run(app, host=host, port=port, reload=False, log_config=None)
    except Exception:
        try:
            (LOGS_DIR / "uvicorn_error.log").write_text(
                traceback.format_exc(), encoding="utf-8"
            )
        except Exception:
            pass


def main():
    args = sys.argv[1:]

    if "--register" in args:
        ok = scheduler.register()
        if ok:
            ConfigManager().update_settings({"registered_as_startup": True})
        print("[OK] 시작 프로그램 등록 완료" if ok else "[FAIL] 등록 실패")
        return

    if "--unregister" in args:
        ok = scheduler.unregister()
        print("[OK] 시작 프로그램 해제 완료" if ok else "[FAIL] 해제 실패")
        return

    if "--status" in args:
        registered = scheduler.is_registered()
        print(f"시작 프로그램 등록 상태: {'[등록됨]' if registered else '[미등록]'}")
        return

    if "--protocol-register" in args:
        ok = scheduler.register_protocol()
        print("[OK] URL 프로토콜 등록 완료 (bhandless://)" if ok else "[FAIL] 프로토콜 등록 실패")
        return

    if "--protocol-unregister" in args:
        ok = scheduler.unregister_protocol()
        print("[OK] URL 프로토콜 해제 완료" if ok else "[FAIL] 프로토콜 해제 실패")
        return

    # bhandless:// 링크로 실행된 경우
    if any(a.startswith("bhandless://") for a in args):
        import socket
        import threading
        import uvicorn
        from api.server import app as fastapi_app
        from core.tray import run_tray

        _cm = ConfigManager()
        _port = _cm.get_settings().get("api_port", 8000)
        try:
            s = socket.create_connection((SERVER_HOST, _port), timeout=1)
            s.close()
            # 서버 이미 실행 중 → 아무것도 하지 않고 종료 (PWA가 재연결 감지)
            return
        except OSError:
            pass  # 서버 꺼져 있음 → 서버 + 트레이만 시작 (시작 항목 실행 안 함)

        threading.Thread(
            target=lambda: _run_uvicorn(fastapi_app, SERVER_HOST, _port),
            daemon=True,
        ).start()
        run_tray(_port)
        return

    if "--serve" in args:
        import threading
        import webbrowser
        from api.server import app

        port = ConfigManager().get_settings().get("api_port", 8000)
        url = f"http://{SERVER_HOST}:{port}"
        print(f"[B-Handless] 서버 시작 → {url}")

        def _open_browser():
            import time
            time.sleep(1.5)
            webbrowser.open(url)

        threading.Thread(target=_open_browser, daemon=True).start()
        _run_uvicorn(app, SERVER_HOST, port)
        return

    import threading
    import uvicorn
    from api.server import app as fastapi_app
    from core.tray import run_tray

    cm = ConfigManager()
    config = cm.load()
    port = cm.get_settings().get("api_port", 8000)

    # 시작 항목 런치 (서버 시작과 병렬로)
    threading.Thread(target=lambda: launch_all(config), daemon=False).start()

    # FastAPI 서버 (트레이 종료 시 같이 죽도록 daemon)
    threading.Thread(
        target=lambda: _run_uvicorn(fastapi_app, SERVER_HOST, port),
        daemon=True,
    ).start()

    # 트레이 아이콘 (메인 스레드 점유, 종료 선택 시 프로세스 종료)
    run_tray(port)


if __name__ == "__main__":
    main()
