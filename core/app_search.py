from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

_app_cache: list[dict] | None = None
_cache_ts: float = 0
_CACHE_TTL = 300  # 5분

_icon_cache: dict[str, str] = {}

_SCAN_PS = r"""
$ErrorActionPreference = 'SilentlyContinue'
$shell = New-Object -ComObject WScript.Shell
$results = [System.Collections.Generic.List[hashtable]]::new()

$dirs = @(
    "$env:ProgramData\Microsoft\Windows\Start Menu\Programs",
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
)
foreach ($dir in $dirs) {
    Get-ChildItem $dir -Filter "*.lnk" -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $lnk = $shell.CreateShortcut($_.FullName)
            $target = $lnk.TargetPath
            if ($target -and $target -match '\.(exe|cmd|bat)$' -and (Test-Path $target)) {
                $results.Add(@{ name = $_.BaseName; path = $target })
            }
        } catch {}
    }
}

$seen = @{}
$unique = $results | Where-Object {
    $key = $_.path.ToLower()
    if (-not $seen[$key]) { $seen[$key] = $true; $true } else { $false }
}

$unique | ConvertTo-Json -Depth 2 -Compress
"""


def scan_installed_apps() -> list[dict]:
    global _app_cache, _cache_ts

    now = time.time()
    if _app_cache is not None and (now - _cache_ts) < _CACHE_TTL:
        return _app_cache

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", _SCAN_PS],
            capture_output=True, text=True, timeout=15,
            creationflags=_NO_WINDOW,
        )
        raw = result.stdout.strip()
        if not raw:
            data: list[dict] = []
        else:
            parsed = json.loads(raw)
            data = [parsed] if isinstance(parsed, dict) else parsed
        _app_cache = data
        _cache_ts = now
    except Exception:
        _app_cache = _app_cache or []

    return _app_cache


def search_apps(q: str) -> list[dict]:
    """검색어로 앱 목록 필터링 (최대 20개)"""
    if not q or not q.strip():
        return []
    apps = scan_installed_apps()
    q_lower = q.lower()
    matched = [a for a in apps if q_lower in a.get("name", "").lower()]
    return matched[:20]


def get_icon_b64(path: str) -> str | None:
    """exe 경로에서 아이콘을 추출해 base64 PNG로 반환"""
    if path in _icon_cache:
        return _icon_cache[path] or None

    if not Path(path).exists():
        return None

    escaped = path.replace("'", "''")
    ps_cmd = f"""
$ErrorActionPreference = 'SilentlyContinue'
try {{
    Add-Type -AssemblyName System.Drawing
    $icon = [System.Drawing.Icon]::ExtractAssociatedIcon('{escaped}')
    if ($icon) {{
        $bmp = $icon.ToBitmap()
        $ms = New-Object System.IO.MemoryStream
        $bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
        [Convert]::ToBase64String($ms.ToArray())
    }}
}} catch {{}}
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=5,
            creationflags=_NO_WINDOW,
        )
        data = result.stdout.strip()
        icon = data if data else None
    except Exception:
        icon = None

    _icon_cache[path] = icon or ""
    return icon or None
