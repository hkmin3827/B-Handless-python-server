"""
Windows 시작 프로그램 등록/해제 모듈

→ 관리자 권한 불필요, 현재 사용자 로그인 시 자동 실행
"""

import sys
import winreg
from pathlib import Path

APP_NAME = "B-Handless"
_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _build_run_command() -> str:
    """
    레지스트리에 등록할 실행 명령어 반환.
    - PyInstaller .exe 패키징 후: exe 경로 그대로
    - 개발 모드: pythonw.exe + main.py 경로 (콘솔 창 없이 실행)
    """
    if getattr(sys, "frozen", False):
        # PyInstaller로 패키징된 .exe
        return f'"{sys.executable}"'

    # 개발 모드: pythonw.exe 사용 (콘솔 창 없이 백그라운드 실행)
    python_dir = Path(sys.executable).parent
    pythonw = python_dir / "pythonw.exe"
    if not pythonw.exists():
        pythonw = Path(sys.executable)  # fallback: python.exe

    main_py = Path(__file__).parent.parent / "main.py"
    return f'"{pythonw}" "{main_py}"'


def is_registered() -> bool:
    """Windows 시작 프로그램에 B-Handless가 등록돼 있는지 확인"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def register() -> bool:
    """Windows 시작 프로그램에 등록 (로그인 시 자동 실행)"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _build_run_command())
        winreg.CloseKey(key)
        return True
    except OSError as e:
        print(f"[ERROR] 시작 프로그램 등록 실패: {e}")
        return False


def unregister() -> bool:
    """
    Windows 시작 프로그램에서 제거.
    서비스 내 '시작 프로그램 해제' 버튼과 연동됨.
    → 서비스에서 삭제 시 레지스트리에서도 동시 제거.
    """
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return True  # 이미 없으면 성공으로 처리
    except OSError as e:
        print(f"[ERROR] 시작 프로그램 해제 실패: {e}")
        return False
