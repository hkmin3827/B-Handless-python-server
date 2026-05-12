"""
Windows 시작 프로그램 등록/해제 모듈

→ 관리자 권한 불필요, 현재 사용자 로그인 시 자동 실행
"""

import sys
import winreg
from pathlib import Path

APP_NAME = "B-Handless"
_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_PROTOCOL = "bhandless"
_PROTOCOL_KEY = rf"SOFTWARE\Classes\{_PROTOCOL}"


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


def register_protocol() -> bool:
    """bhandless:// URL 프로토콜 핸들러 등록 (브라우저에서 B-Handless.exe 실행 가능)"""
    try:
        exe_cmd = _build_run_command().rstrip('"') + '" "%1"'

        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, _PROTOCOL_KEY)
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f"URL:{APP_NAME} Protocol")
        winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
        winreg.CloseKey(key)

        cmd_key = winreg.CreateKey(
            winreg.HKEY_CURRENT_USER, rf"{_PROTOCOL_KEY}\shell\open\command"
        )
        winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, exe_cmd)
        winreg.CloseKey(cmd_key)
        return True
    except OSError as e:
        print(f"[ERROR] 프로토콜 등록 실패: {e}")
        return False


def unregister_protocol() -> bool:
    """bhandless:// URL 프로토콜 핸들러 제거"""
    import shutil

    def _delete_key_tree(hive, path: str) -> bool:
        try:
            key = winreg.OpenKey(hive, path, 0, winreg.KEY_ALL_ACCESS)
            # 하위 키 먼저 재귀 삭제
            while True:
                try:
                    sub = winreg.EnumKey(key, 0)
                    _delete_key_tree(hive, rf"{path}\{sub}")
                except OSError:
                    break
            winreg.CloseKey(key)
            winreg.DeleteKey(hive, path)
            return True
        except FileNotFoundError:
            return True
        except OSError as e:
            print(f"[ERROR] 키 삭제 실패 {path}: {e}")
            return False

    return _delete_key_tree(winreg.HKEY_CURRENT_USER, _PROTOCOL_KEY)


def is_protocol_registered() -> bool:
    """bhandless:// 프로토콜이 등록돼 있는지 확인"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _PROTOCOL_KEY, 0, winreg.KEY_READ)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except OSError:
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
