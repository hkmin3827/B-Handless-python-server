"""
시스템 트레이 아이콘 관리
- 부팅 시 백그라운드 상주
- 우클릭 메뉴: 대시보드 열기 / 종료
"""

import subprocess
import threading
import webbrowser
import winreg

import pystray
from PIL import Image, ImageDraw, ImageFont

from core.security import SERVER_HOST


def _open_pwa(url: str) -> None:
    """설치된 PWA 앱 모드로 URL 열기. Edge → Chrome → 기본 브라우저 순으로 시도."""
    for exe_name in ("msedge.exe", "chrome.exe"):
        key_path = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}"
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                key = winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ)
                browser_path, _ = winreg.QueryValueEx(key, "")
                winreg.CloseKey(key)
                subprocess.Popen([browser_path, f"--app={url}"])
                return
            except (FileNotFoundError, OSError):
                continue
    webbrowser.open(url)


def _make_icon_image() -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 파란 원 배경
    draw.ellipse([2, 2, size - 2, size - 2], fill=(37, 99, 235, 255))

    # 흰색 "B" 텍스트 (기본 폰트 사용)
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except OSError:
        font = ImageFont.load_default()

    text = "B"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) // 2 - bbox[0]
    ty = (size - th) // 2 - bbox[1]
    draw.text((tx, ty), text, fill=(255, 255, 255, 255), font=font)

    return img


def run_tray(port: int) -> None:
    """트레이 아이콘 실행 (메인 스레드에서 호출, 종료 시까지 블로킹)"""
    url = f"http://{SERVER_HOST}:{port}"

    def on_open(icon, item):
        _open_pwa(url)

    def on_quit(icon, item):
        icon.stop()

    icon = pystray.Icon(
        name="B-Handless",
        icon=_make_icon_image(),
        title=f"B-Handless  |  {url}",
        menu=pystray.Menu(
            pystray.MenuItem("대시보드 열기", on_open, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("B-Handless 종료", on_quit),
        ),
    )
    icon.run()
