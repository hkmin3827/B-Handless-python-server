"""
API 서버 보안 설정 및 입력 검증 유틸리티

- API 서버는 반드시 host="127.0.0.1" 바인딩 (외부 접근 차단)
- CORS는 localhost 출처만 허용
- 실행 파일 경로는 이 모듈의 함수를 통해 검증
"""

from pathlib import Path

# 업로드된 실행 파일은 이 디렉토리 안에서만 실행 허용
UPLOADS_DIR = (Path(__file__).parent.parent / "uploads").resolve()

# 실행 허용 확장자
_ALLOWED_EXTENSIONS = {".exe", ".bat", ".cmd", ".lnk"}

# 지원 브라우저 — 키: config에서 사용할 이름, 값: App Paths 레지스트리 키에 등록된 exe 파일명
# Safari는 Windows 미지원(2012년 Apple 공식 중단)으로 제외
SUPPORTED_BROWSERS: dict[str, str] = {
    "edge":    "msedge.exe",
    "chrome":  "chrome.exe",
    "firefox": "firefox.exe",
    "opera":   "opera.exe",
}

# FastAPI 서버 바인딩 설정 — 외부에서 절대 변경하지 말 것
SERVER_HOST = "127.0.0.1"

# CORS 허용 출처 목록
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def validate_exe_path(path: str) -> Path:
    """
    실행 파일 경로를 검증하고 정규화된 Path 반환.

    규칙:
    - 상대 경로: uploads/ 내부만 허용 (경로 순회 차단)
    - 절대 경로: 파일 존재 확인 + 허용 확장자 확인
    - '..' 포함 경로: 정규화 후 uploads/ 탈출 여부 검사

    Raises:
        ValueError: 검증 실패 시
    """
    if not path or not path.strip():
        raise ValueError("path가 비어 있습니다.")

    raw = Path(path)

    if raw.is_absolute():
        resolved = raw.resolve()
    else:
        resolved = (Path(__file__).parent.parent / raw).resolve()

    # 확장자 화이트리스트
    if resolved.suffix.lower() not in _ALLOWED_EXTENSIONS:
        raise ValueError(
            f"허용되지 않은 확장자입니다: '{resolved.suffix}' "
            f"(허용: {', '.join(_ALLOWED_EXTENSIONS)})"
        )

    # 상대 경로인 경우 uploads/ 내부인지 확인 (경로 순회 차단)
    if not raw.is_absolute():
        try:
            resolved.relative_to(UPLOADS_DIR)
        except ValueError:
            raise ValueError(
                f"상대 경로는 uploads/ 내부만 허용됩니다: '{path}'"
            )

    return resolved


def validate_url(url: str) -> str:
    """
    URL이 http:// 또는 https:// 로 시작하는지 확인.

    Raises:
        ValueError: 잘못된 URL 형식
    """
    if not url or not url.strip():
        raise ValueError("url이 비어 있습니다.")

    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError(f"URL은 http:// 또는 https://로 시작해야 합니다: '{url}'")

    return url


def validate_item(item: dict) -> dict:
    """
    config 항목 전체를 검증. 타입별로 필수 필드와 값 검사.

    Raises:
        ValueError: 검증 실패 시
    """
    item_type = item.get("type", "")

    if item_type == "browser_url":
        validate_url(item.get("url", ""))
        browser = item.get("browser", "edge").lower()
        if browser not in SUPPORTED_BROWSERS:
            raise ValueError(
                f"지원하지 않는 브라우저입니다: '{browser}' "
                f"(선택 가능: {', '.join(SUPPORTED_BROWSERS)})"
            )

    elif item_type in ("exe", "app", "uploaded_exe"):
        validate_exe_path(item.get("path", ""))

    else:
        raise ValueError(f"알 수 없는 타입입니다: '{item_type}'")

    delay = item.get("delay_seconds", 0)
    if not isinstance(delay, (int, float)) or delay < 0:
        raise ValueError(f"delay_seconds는 0 이상의 숫자여야 합니다: {delay}")

    return item
