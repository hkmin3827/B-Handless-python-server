"""
  python main.py              → 시작 항목 전체 실행 (부팅 시 자동 호출)
  python main.py --register   → Windows 시작 프로그램에 등록
  python main.py --unregister → Windows 시작 프로그램에서 제거
  python main.py --status     → 등록 상태 확인
"""

import sys
from core.config_manager import ConfigManager
from core.launcher import launch_all
from core import scheduler


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

    cm = ConfigManager()
    config = cm.load()
    launch_all(config)


if __name__ == "__main__":
    main()
