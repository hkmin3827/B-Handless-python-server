# B-Handless — Server

> 부팅 시 사용자의 작업환경을 자동으로 세팅하는 Windows 자동화 서비스.  
> 로그인하면 지정한 앱·브라우저·실행 파일이 자동으로 켜진다.

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [요구사항 명세서](#2-요구사항-명세서)
3. [기능 명세서](#3-기능-명세서)
4. [사용 기술](#4-사용-기술)
5. [시스템 플로우](#5-시스템-플로우)
6. [디렉토리 구조](#6-디렉토리-구조)
7. [설정 파일 스키마](#7-설정-파일-스키마)
8. [설치 및 실행](#8-설치-및-실행)

---

## 1. 프로젝트 개요

### 배경

매일 PC를 켤 때마다 같은 앱을 열고, 같은 브라우저 탭을 띄우고, 같은 서버를 실행하는 반복 작업을 없애기 위해 만들었다. 부팅 후 로그인하면 사전에 등록한 항목들이 자동으로 실행되어 즉시 작업 가능한 환경이 세팅된다.

### 핵심 목표

- **자동화**: 부팅만 하면 작업환경이 완성된다
- **유연성**: 브라우저 URL, 앱 실행 파일, 업로드된 .exe를 모두 지원
- **직접 제어**: Windows 시작 프로그램 등록·해제를 서비스 안에서 모두 처리
- **확장 가능**: 로컬 전용으로 시작하지만 배포 환경(클라우드 API)으로 확장 가능한 구조

### 구성

이 레포는 백엔드(Python) 단독 레포다.  
프론트엔드(React 대시보드)는 별도 레포 `b-handless-dashboard`에서 관리한다.

| 레포 | 역할 |
|------|------|
| `b-handless-server` (이 레포) | 실행 엔진 + Windows 제어 + REST API |
| `b-handless-dashboard` | 설정 UI (React + Vite, PWA) |

---

## 2. 요구사항 명세서

### 2-1. 기능 요구사항

#### FR-01. 시작 항목 실행

| ID | 요구사항 | 우선순위 |
|----|----------|---------|
| FR-01-1 | 지정한 URL을 Microsoft Edge에서 자동으로 연다 | 필수 |
| FR-01-2 | 지정한 경로의 실행 파일(.exe)을 자동으로 실행한다 | 필수 |
| FR-01-3 | 일반 앱(경로 지정)을 자동으로 실행한다 | 필수 |
| FR-01-4 | `uploads/` 디렉토리에 올려진 .exe를 자동으로 실행한다 | 필수 |
| FR-01-5 | 각 항목마다 실행 전 대기 시간(delay_seconds)을 설정할 수 있다 | 필수 |
| FR-01-6 | 여러 항목이 각자의 delay에 따라 병렬로 실행된다 | 필수 |
| FR-01-7 | 항목별로 활성화/비활성화를 토글할 수 있다 | 필수 |

#### FR-02. 시작 항목 관리

| ID | 요구사항 | 우선순위 |
|----|----------|---------|
| FR-02-1 | 시작 항목을 추가할 수 있다 | 필수 |
| FR-02-2 | 시작 항목을 수정할 수 있다 | 필수 |
| FR-02-3 | 시작 항목을 삭제할 수 있다 | 필수 |
| FR-02-4 | 시작 항목 목록을 조회할 수 있다 | 필수 |
| FR-02-5 | 특정 항목을 즉시 실행할 수 있다 (대시보드 테스트용) | 필수 |

#### FR-03. Windows 시작 프로그램 제어

| ID | 요구사항 | 우선순위 |
|----|----------|---------|
| FR-03-1 | B-Handless를 Windows 시작 프로그램에 등록한다 | 필수 |
| FR-03-2 | B-Handless를 Windows 시작 프로그램에서 해제한다 | 필수 |
| FR-03-3 | 현재 등록 상태를 조회할 수 있다 | 필수 |
| FR-03-4 | 서비스 내 해제 시 레지스트리에서도 동시에 제거된다 | 필수 |

#### FR-04. REST API (Phase 3 예정)

| ID | 요구사항 | 우선순위 |
|----|----------|---------|
| FR-04-1 | 시작 항목 CRUD API를 제공한다 | 필수 |
| FR-04-2 | 특정 항목 즉시 실행 API를 제공한다 | 필수 |
| FR-04-3 | 시작 프로그램 등록·해제 API를 제공한다 | 필수 |
| FR-04-4 | .exe 파일 업로드 API를 제공한다 | 필수 |
| FR-04-5 | 실행 로그 조회 API를 제공한다 | 선택 |

#### FR-05. 실행 파일 업로드 (Phase 3 예정)

| ID | 요구사항 | 우선순위 |
|----|----------|---------|
| FR-05-1 | 사용자가 .exe 파일을 업로드할 수 있다 | 필수 |
| FR-05-2 | 업로드된 파일은 `uploads/` 디렉토리에 저장된다 | 필수 |
| FR-05-3 | 업로드 후 해당 .exe가 시작 항목으로 자동 등록된다 | 필수 |

---

### 2-2. 비기능 요구사항

| ID | 요구사항 |
|----|----------|
| NFR-01 | Windows 10 / 11 환경에서 동작한다 |
| NFR-02 | Python 3.11 이상에서 동작한다 |
| NFR-03 | 관리자 권한 없이 현재 사용자 권한으로 동작한다 |
| NFR-04 | Phase 1 핵심 엔진은 외부 패키지 없이 Python 표준 라이브러리만 사용한다 |
| NFR-05 | 실행 로그를 `logs/startup.log`에 기록한다 |
| NFR-06 | .env, *.key, *.pem 등 민감 파일은 git에 포함하지 않는다 |
| NFR-07 | API 서버는 localhost에서만 접근 가능하도록 기본 설정한다 |
| NFR-08 | PyInstaller로 단일 .exe 패키징이 가능한 구조를 유지한다 |

---

## 3. 기능 명세서

### 3-1. 실행 엔진 (`core/launcher.py`)

부팅 시 config.json을 읽어 등록된 항목들을 실행하는 핵심 모듈.

#### 지원 실행 타입

| type | 설명 | 필수 필드 |
|------|------|----------|
| `browser_url` | URL을 Edge 또는 기본 브라우저에서 오픈 | `url`, `browser` |
| `exe` | 절대/상대 경로의 .exe 실행 | `path` |
| `app` | 절대/상대 경로의 앱 실행 (`exe`와 동일 동작) | `path` |
| `uploaded_exe` | `uploads/` 디렉토리 내 .exe 실행 | `path` (상대경로) |

#### 실행 흐름

```
launch_all(config)
    │
    ├── enabled=true 항목 필터링
    │
    └── 각 항목 → 독립 스레드 생성
            │
            ├── delay_seconds 대기 (각자 독립 타이머)
            │
            └── launch_item(item)
                    ├── browser_url → Edge 경로 탐지 → Popen
                    ├── exe / app   → 경로 검증 → Popen
                    └── uploaded_exe → 상대경로 해석 → Popen
```

#### 주요 동작 규칙

- Edge 경로를 자동 탐지한다 (`Program Files (x86)` → `Program Files` 순서로 확인)
- Edge를 찾지 못하면 시스템 기본 브라우저로 fallback한다
- 상대 경로는 프로젝트 루트(`server/`) 기준으로 해석한다
- 파일이 존재하지 않으면 오류 로그만 기록하고 다음 항목을 계속 실행한다
- 모든 실행 결과는 `logs/startup.log`에 타임스탬프와 함께 기록한다

---

### 3-2. 설정 관리 (`core/config_manager.py`)

`config.json`의 읽기·쓰기·CRUD를 담당하는 모듈.

#### 제공 메서드

| 메서드 | 설명 |
|--------|------|
| `load()` | config.json 전체 로드. 파일 없으면 기본값으로 생성 |
| `save(config)` | config.json 전체 저장 |
| `get_items()` | 시작 항목 목록 반환 |
| `get_item(id)` | 특정 ID의 항목 반환. 없으면 None |
| `add_item(item)` | 항목 추가. ID는 자동 생성(uuid 앞 8자리) |
| `update_item(id, updates)` | 특정 항목 부분 수정 |
| `toggle_item(id)` | enabled 값 반전 |
| `delete_item(id)` | 항목 삭제. 성공 여부 bool 반환 |
| `get_settings()` | settings 섹션 반환 |
| `update_settings(updates)` | settings 부분 수정 |

---

### 3-3. 시작 프로그램 제어 (`core/scheduler.py`)

Windows 레지스트리를 직접 조작해 로그인 시 자동 실행을 제어하는 모듈.

#### 레지스트리 경로

```
HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
키 이름: B-Handless
```

> `HKEY_CURRENT_USER` 사용으로 **관리자 권한 불필요**.

#### 제공 함수

| 함수 | 설명 |
|------|------|
| `is_registered()` | 현재 등록 여부 확인 (bool) |
| `register()` | 레지스트리에 실행 명령어 등록 |
| `unregister()` | 레지스트리에서 항목 제거 |

#### 실행 명령어 결정 로직

```
패키징 환경 (PyInstaller .exe)
    → "{exe 경로}"

개발 환경 (python main.py)
    → "{pythonw.exe 경로}" "{main.py 절대경로}"
    ※ pythonw.exe: 콘솔 창 없이 백그라운드 실행
```

---

### 3-4. REST API (`api/server.py`) — Phase 3 예정

대시보드(React)와 통신하기 위한 FastAPI 서버.  
`localhost:8000`에서 실행되며 CORS는 `localhost:3000`만 허용.

#### 예정 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/items` | 시작 항목 전체 조회 |
| `POST` | `/items` | 항목 추가 |
| `PUT` | `/items/{id}` | 항목 수정 |
| `DELETE` | `/items/{id}` | 항목 삭제 |
| `PATCH` | `/items/{id}/toggle` | 활성화/비활성화 토글 |
| `POST` | `/items/{id}/run` | 특정 항목 즉시 실행 |
| `POST` | `/items/upload` | .exe 파일 업로드 후 항목 등록 |
| `GET` | `/settings` | 전체 설정 조회 |
| `PATCH` | `/settings/startup` | 시작 프로그램 등록·해제 |
| `GET` | `/logs` | 최근 실행 로그 조회 |

---

### 3-5. 진입점 (`main.py`)

| 실행 명령 | 동작 |
|----------|------|
| `python main.py` | config.json 읽어 시작 항목 전체 실행 (부팅 시 자동 호출) |
| `python main.py --register` | Windows 시작 프로그램에 등록 |
| `python main.py --unregister` | Windows 시작 프로그램에서 해제 |
| `python main.py --status` | 현재 등록 상태 출력 |

---

## 4. 사용 기술

### 현재 (Phase 1)

| 기술 | 버전 | 용도 |
|------|------|------|
| Python | 3.11+ | 전체 런타임 |
| `subprocess` | 표준 라이브러리 | 앱·exe 실행 |
| `threading` | 표준 라이브러리 | delay 병렬 처리 |
| `winreg` | 표준 라이브러리 (Windows 내장) | 레지스트리 읽기/쓰기 |
| `webbrowser` | 표준 라이브러리 | 기본 브라우저 fallback |
| `logging` | 표준 라이브러리 | 실행 로그 기록 |
| `json` | 표준 라이브러리 | config.json 파싱 |
| `uuid` | 표준 라이브러리 | 항목 ID 자동 생성 |
| `pathlib` | 표준 라이브러리 | 경로 처리 |

> Phase 1은 **외부 패키지 설치 없이** 동작한다.

### Phase 3 추가 예정

| 기술 | 버전 | 용도 |
|------|------|------|
| FastAPI | 0.111+ | REST API 서버 |
| Uvicorn | 0.29+ | ASGI 서버 (FastAPI 구동) |
| psutil | 5.9+ | 프로세스 실행 중 여부 확인 |

### Phase 5 추가 예정

| 기술 | 버전 | 용도 |
|------|------|------|
| PyInstaller | 6.0+ | 단일 .exe 패키징 |

---

## 5. 시스템 플로우

### 부팅 시 자동 실행 플로우

```
[Windows 로그인]
      │
      ▼
[레지스트리 Run 키 실행]
  HKCU\...\Run\B-Handless
      │
      ▼
[main.py 실행] (pythonw.exe — 콘솔 창 없음)
      │
      ▼
[config.json 로드]
      │
      ├── startup_items 중 enabled=true 필터링
      │
      └── 각 항목 → 스레드 분리
              │
              ├── delay_seconds 대기
              │
              ├── [browser_url] → Edge 탐지 → msedge.exe {url}
              ├── [exe / app]   → 경로 확인 → Popen({path})
              └── [uploaded_exe]→ uploads/ 경로 해석 → Popen({path})
```

### 시작 프로그램 등록/해제 플로우

```
[사용자: 대시보드에서 '시작 프로그램 등록' 토글]  (Phase 3 이후)
      │
      ▼
[FastAPI PATCH /settings/startup]
      │
      ├── register=true  → scheduler.register()
      │       └── winreg SetValueEx → HKCU\...\Run 에 실행 명령어 기록
      │
      └── register=false → scheduler.unregister()
              └── winreg DeleteValue → HKCU\...\Run 에서 항목 제거
```

### .exe 업로드 → 시작 항목 등록 플로우 (Phase 3 예정)

```
[사용자: 대시보드에서 .exe 파일 업로드]
      │
      ▼
[FastAPI POST /items/upload]
      │
      ├── 파일을 uploads/{label}/ 에 저장
      │
      ├── config.json에 uploaded_exe 항목 추가
      │   {type: "uploaded_exe", path: "uploads/{label}/{file}.exe"}
      │
      └── 다음 부팅부터 자동 실행
```

---

## 6. 디렉토리 구조

```
server/
│
├── main.py                # 진입점 (부팅 자동 실행 / CLI 제어)
├── config.json            # 시작 항목 및 설정 (사용자 편집 가능)
├── requirements.txt       # 패키지 목록
├── .gitignore
│
├── core/
│   ├── __init__.py
│   ├── launcher.py        # 실행 엔진 (앱·URL·exe 실행)
│   ├── config_manager.py  # config.json CRUD
│   └── scheduler.py       # Windows 레지스트리 제어
│
├── api/                   # Phase 3에 추가
│   └── server.py          # FastAPI 서버
│
├── uploads/               # 업로드된 .exe 보관 (gitignore 대상)
│   └── .gitkeep
│
└── logs/                  # 실행 로그 (gitignore 대상)
    └── startup.log
```

---

## 7. 설정 파일 스키마

`config.json` 전체 구조:

```json
{
  "startup_items": [항목 배열],
  "settings": {설정 객체}
}
```

### startup_items 항목 공통 필드

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `id` | string | 자동 생성 | 8자리 UUID (예: `"a1b2c3d4"`) |
| `type` | string | 필수 | `browser_url` / `exe` / `app` / `uploaded_exe` |
| `label` | string | 필수 | 화면에 표시될 이름 |
| `enabled` | bool | 기본 true | false이면 부팅 시 건너뜀 |
| `delay_seconds` | int | 기본 0 | 실행 전 대기 시간 (초) |

### 타입별 추가 필드

**browser_url**
```json
{
  "url": "https://example.com",
  "browser": "edge"
}
```

| 필드 | 값 | 설명 |
|------|----|------|
| `url` | URL 문자열 | 열 주소 |
| `browser` | `"edge"` / `"default"` | edge: msedge.exe 직접 실행, default: 시스템 기본 |

**exe / app / uploaded_exe**
```json
{
  "path": "C:/path/to/app.exe",
  "args": ["--flag", "value"]
}
```

| 필드 | 값 | 설명 |
|------|----|------|
| `path` | 절대경로 또는 상대경로 | 상대경로는 `server/` 기준 |
| `args` | 문자열 배열 | 실행 인자 (생략 가능) |

### settings 필드

| 필드 | 기본값 | 설명 |
|------|--------|------|
| `api_port` | 8000 | FastAPI 서버 포트 |
| `dashboard_port` | 3000 | React 대시보드 포트 |
| `log_enabled` | true | 로그 기록 여부 |
| `registered_as_startup` | false | Windows 시작 프로그램 등록 상태 |

### 전체 예시

```json
{
  "startup_items": [
    {
      "id": "a1b2c3d4",
      "type": "browser_url",
      "label": "아침 뉴스",
      "enabled": true,
      "url": "https://news.naver.com",
      "browser": "edge",
      "delay_seconds": 3
    },
    {
      "id": "e5f6g7h8",
      "type": "uploaded_exe",
      "label": "정보 수집 서버",
      "enabled": true,
      "path": "uploads/my-server/server.exe",
      "args": [],
      "delay_seconds": 0
    },
    {
      "id": "i9j0k1l2",
      "type": "app",
      "label": "VSCode",
      "enabled": true,
      "path": "C:/Users/hkmin/AppData/Local/Programs/Microsoft VS Code/Code.exe",
      "delay_seconds": 5
    }
  ],
  "settings": {
    "api_port": 8000,
    "dashboard_port": 3000,
    "log_enabled": true,
    "registered_as_startup": false
  }
}
```

---

## 8. 설치 및 실행

### 요구사항

- Windows 10 / 11
- Python 3.11 이상

### Phase 1 (현재) — 외부 패키지 없음

```bash
# 1. 레포 클론
git clone https://github.com/{username}/b-handless-server.git
cd b-handless-server

# 2. 바로 실행 (설치 불필요)
python main.py

# 3. Windows 시작 프로그램 등록 (이후 부팅마다 자동 실행)
python main.py --register

# 4. 등록 확인
python main.py --status

# 5. 해제
python main.py --unregister
```

### Phase 3 이후 — FastAPI 포함

```bash
pip install -r requirements.txt
python main.py
```

---

## 개발 현황

| Phase | 내용 | 상태 |
|-------|------|------|
| Phase 1 | Python 핵심 엔진 (launcher, config, scheduler) | 완료 |
| Phase 2 | Windows 시작 프로그램 등록 | 완료 (Phase 1 통합) |
| Phase 3 | FastAPI REST API 서버 | 예정 |
| Phase 4 | React 대시보드 (별도 레포) | 예정 |
| Phase 5 | PyInstaller .exe 패키징 | 예정 |
