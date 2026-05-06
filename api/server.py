import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core.config_manager import ConfigManager
from core.launcher import _find_browser, launch_by_id
from core.security import CORS_ORIGINS, SUPPORTED_BROWSERS

# ── 모바일 차단 ───────────────────────────────────────────────────────────────

_MOBILE_UA = ("android", "iphone", "ipad", "ipod", "mobile", "blackberry",
              "windows phone", "opera mini", "silk")

_ASSET_EXTS = (".js", ".css", ".png", ".ico", ".svg", ".json",
               ".woff", ".woff2", ".ttf", ".webmanifest")


def _is_mobile(request: Request) -> bool:
    ua = request.headers.get("user-agent", "").lower()
    return any(kw in ua for kw in _MOBILE_UA)


# ── 앱 초기화 ─────────────────────────────────────────────────────────────────

app = FastAPI(title="B-Handless API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def block_mobile(request: Request, call_next):
    path = request.url.path
    is_asset = any(path.endswith(ext) for ext in _ASSET_EXTS)
    if not is_asset and _is_mobile(request):
        return JSONResponse(
            status_code=403,
            content={"detail": "B-Handless는 데스크톱 전용 앱입니다."},
        )
    return await call_next(request)


# ── API 라우터 (/api prefix) ──────────────────────────────────────────────────

router = APIRouter(prefix="/api")
cm = ConfigManager()


class ItemBody(BaseModel):
    type: str
    label: str
    enabled: bool = True
    delay_seconds: float = Field(default=0, ge=0)
    url: str | None = None
    browser: str | None = None
    path: str | None = None
    args: list[str] = []

class ItemUpdate(BaseModel):
    label: str | None = None
    enabled: bool | None = None
    delay_seconds: float | None = Field(default=None, ge=0)
    url: str | None = None
    browser: str | None = None
    path: str | None = None
    args: list[str] | None = None

class SettingsUpdate(BaseModel):
    api_port: int | None = Field(default=None, ge=1, le=65535)
    dashboard_port: int | None = Field(default=None, ge=1, le=65535)
    log_enabled: bool | None = None


@router.get("/items")
def list_items() -> list[dict]:
    return cm.get_items()

@router.get("/items/{item_id}")
def get_item(item_id: str) -> dict:
    item = cm.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"항목을 찾을 수 없습니다: {item_id}")
    return item

@router.post("/items", status_code=201)
def add_item(body: ItemBody) -> dict:
    try:
        return cm.add_item(body.model_dump(exclude_none=False))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@router.patch("/items/{item_id}")
def update_item(item_id: str, body: ItemUpdate) -> dict:
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=422, detail="변경할 필드를 하나 이상 전달해야 합니다.")
    try:
        result = cm.update_item(item_id, updates)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail=f"항목을 찾을 수 없습니다: {item_id}")
    return result

@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: str):
    if not cm.delete_item(item_id):
        raise HTTPException(status_code=404, detail=f"항목을 찾을 수 없습니다: {item_id}")

@router.post("/items/{item_id}/toggle")
def toggle_item(item_id: str) -> dict:
    result = cm.toggle_item(item_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"항목을 찾을 수 없습니다: {item_id}")
    return result

@router.post("/items/{item_id}/run")
def run_item(item_id: str) -> dict[str, Any]:
    config = cm.load()
    ok = launch_by_id(config, item_id)
    if not ok:
        raise HTTPException(status_code=404,
                            detail=f"항목을 찾을 수 없거나 실행에 실패했습니다: {item_id}")
    return {"ok": True, "item_id": item_id}

@router.get("/settings")
def get_settings() -> dict:
    return cm.get_settings()

@router.patch("/settings")
def update_settings(body: SettingsUpdate) -> dict:
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=422, detail="변경할 필드를 하나 이상 전달해야 합니다.")
    cm.update_settings(updates)
    return cm.get_settings()

@router.get("/browsers")
def list_browsers() -> list[dict[str, Any]]:
    return [
        {"id": name, "label": name.capitalize(), "installed": _find_browser(name) is not None}
        for name in SUPPORTED_BROWSERS
    ]


# ── 라우터 등록 + 정적 파일 서빙 ──────────────────────────────────────────────

app.include_router(router)


def _web_dir() -> Path:
    if getattr(sys, "frozen", False):          # PyInstaller 번들
        return Path(sys._MEIPASS) / "web"      # type: ignore[attr-defined]
    return Path(__file__).parent.parent / "web"


_WEB = _web_dir()
if _WEB.exists():
    app.mount("/", StaticFiles(directory=str(_WEB), html=True), name="static")
