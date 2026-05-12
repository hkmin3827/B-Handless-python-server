import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.routing import APIRouter
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from user_agents import parse as parse_ua

from core.app_search import get_icon_b64, search_apps
from core.config_manager import ConfigManager
from core.launcher import _find_browser, launch_by_id
from core import scheduler
from core.security import CORS_ORIGINS, SUPPORTED_BROWSERS

_MOBILE_PATH = "/mobile"

_ASSET_EXTS = (".js", ".css", ".png", ".ico", ".svg", ".json",
               ".woff", ".woff2", ".ttf", ".webmanifest")

_MOBILE_GUIDE_HTML = (Path(__file__).parent / "mobile.html").read_text(encoding="utf-8")


def _is_mobile(request: Request) -> bool:
    ua = parse_ua(request.headers.get("user-agent", ""))
    return ua.is_mobile or ua.is_tablet


app = FastAPI(title="B-Handless API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get(_MOBILE_PATH, response_class=HTMLResponse, include_in_schema=False)
async def mobile_guide():
    return HTMLResponse(content=_MOBILE_GUIDE_HTML)


@app.middleware("http")
async def block_mobile(request: Request, call_next):
    path = request.url.path
    is_asset = any(path.endswith(ext) for ext in _ASSET_EXTS)
    if not is_asset and path != _MOBILE_PATH and _is_mobile(request):
        return RedirectResponse(url=_MOBILE_PATH, status_code=302)
    return await call_next(request)


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
        data = body.model_dump(exclude_none=False)
        if data.get("type") in ("app", "exe", "uploaded_exe") and data.get("path"):
            icon = get_icon_b64(data["path"])
            if icon:
                data["icon_b64"] = icon
        return cm.add_item(data)
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
    settings = cm.get_settings()
    # config.json 값 대신 레지스트리 실제 상태를 반환
    settings["registered_as_startup"] = scheduler.is_registered()
    return settings

@router.patch("/settings")
def update_settings(body: SettingsUpdate) -> dict:
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=422, detail="변경할 필드를 하나 이상 전달해야 합니다.")
    cm.update_settings(updates)
    settings = cm.get_settings()
    settings["registered_as_startup"] = scheduler.is_registered()
    return settings

@router.post("/startup/register")
def register_startup() -> dict[str, Any]:
    ok = scheduler.register()
    if ok:
        cm.update_settings({"registered_as_startup": True})
    return {"ok": ok}

@router.post("/startup/unregister")
def unregister_startup() -> dict[str, Any]:
    ok = scheduler.unregister()
    if ok:
        cm.update_settings({"registered_as_startup": False})
    return {"ok": ok}

@router.get("/apps/search")
def search_installed_apps(q: str = "") -> list[dict]:
    return search_apps(q)

@router.get("/apps/icon")
def get_app_icon(path: str = "") -> dict[str, Any]:
    icon = get_icon_b64(path) if path else None
    return {"icon": icon}

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
