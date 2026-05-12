"""
  python main.py              → 트레이 앱 실행 (서버 + 시작 항목 + 트레이 아이콘)
  python main.py --serve      → FastAPI 서버 실행 (대시보드 연동용)
  python main.py --register   → Windows 시작 프로그램에 등록
  python main.py --unregister → Windows 시작 프로그램에서 제거
  python main.py --status     → 등록 상태 확인
"""

import sys
from core.config_manager import ConfigManager
from core.launcher import launch_all
from core import scheduler
from core.security import SERVER_HOST


def main():
    args = sys.argv[1:]

    if "--register" in args:
        ok = scheduler.register()
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

    if "--serve" in args:
        import threading
        import webbrowser
        import uvicorn
        from core.config_manager import ConfigManager as CM
        from api.server import app

        port = CM().get_settings().get("api_port", 8000)
        url = f"http://{SERVER_HOST}:{port}"
        print(f"[B-Handless] 서버 시작 → {url}")

        def _open_browser():
            import time
            time.sleep(1.5)
            webbrowser.open(url)

        threading.Thread(target=_open_browser, daemon=True).start()
        uvicorn.run(app, host=SERVER_HOST, port=port, reload=False)
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
        target=lambda: uvicorn.run(fastapi_app, host=SERVER_HOST, port=port, reload=False),
        daemon=True,
    ).start()

    # 트레이 아이콘 (메인 스레드 점유, 종료 선택 시 프로세스 종료)
    run_tray(port)


if __name__ == "__main__":
    main()
