# B-Handless — Server

> 부팅 시 사용자의 작업환경을 자동으로 세팅하는 Windows 자동화 서비스.  
> 로그인하면 지정한 앱·브라우저·실행 파일이 자동으로 켜지고, 시스템 트레이에 상주하며 대시보드를 제공한다.

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
- **트레이 상주**: 시스템 트레이 아이콘으로 서버 상태 확인 및 대시보드 접근
- **유연성**: 브라우저 URL, 앱 실행 파일, 업로드된 .exe를 모두 지원
- **직접 제어**: Windows 시작 프로그램 등록·해제를 서비스 안에서 모두 처리
- **PWA 지원**: React 대시보드를 PWA로 설치해 앱처럼 사용 가능

### 구성

이 레포는 백엔드(Python)와 프론트엔드(React)를 함께 관리하는 모노레포다.

| 폴더 | 역할 |
|------|------|
| `server/` | 실행 엔진 + Windows 제어 + REST API |
| `dashboard/` | 설정 UI (React + Vite, PWA) |

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

#### FR-04. REST API

| ID | 요구사항 | 우선순위 |
|----|----------|---------|
| FR-04-1 | 시작 항목 CRUD API를 제공한다 | 필수 |
| FR-04-2 | 특정 항목 즉시 실행 API를 제공한다 | 필수 |
| FR-04-3 | 시작 프로그램 등록·해제 API를 제공한다 | 필수 |
| FR-04-4 | .exe 파일 업로드 API를 제공한다 | 필수 |
| FR-04-5 | 실행 로그 조회 API를 제공한다 | 선택 |

#### FR-05. 실행 파일 업로드

| ID | 요구사항 | 우선순위 |
|----|----------|---------|
| FR-05-1 | 사용자가 .exe 파일을 업로드할 수 있다 | 필수 |
| FR-05-2 | 업로드된 파일은 `uploads/` 디렉토리에 저장된다 | 필수 |
| FR-05-3 | 업로드 후 해당 .exe가 시작 항목으로 자동 등록된다 | 필수 |

#### FR-06. 트레이 앱

| ID | 요구사항 | 우선순위 |
|----|----------|---------|
| FR-06-1 | 부팅 시 시스템 트레이에 아이콘으로 상주한다 | 필수 |
| FR-06-2 | 트레이 우클릭으로 대시보드를 브라우저에서 열 수 있다 | 필수 |
| FR-06-3 | 트레이 우클릭으로 서버를 포함한 전체 프로세스를 종료할 수 있다 | 필수 |

---

### 2-2. 비기능 요구사항

| ID | 요구사항 |
|----|----------|
| NFR-01 | Windows 10 / 11 환경에서 동작한다 |
| NFR-02 | Python 3.11 이상에서 동작한다 |
| NFR-03 | 관리자 권한 없이 현재 사용자 권한으로 동작한다 |
| NFR-04 | 실행 로그를 `logs/startup.log`에 기록한다 |
| NFR-05 | .env, *.key, *.pem 등 민감 파일은 git에 포함하지 않는다 |
| NFR-06 | API 서버는 localhost에서만 접근 가능하도록 기본 설정한다 |
| NFR-07 | PyInstaller로 단일 디렉터리 .exe 패키징이 가능한 구조를 유지한다 |
| NFR-08 | 콘솔 창 없이 백그라운드에서 실행된다 (console=False) |

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
    → "{exe 경로}"  ← 인수 없음 = 기본 모드 (트레이 앱 실행)

개발 환경 (python main.py)
    → "{pythonw.exe 경로}" "{main.py 절대경로}"
    ※ pythonw.exe: 콘솔 창 없이 백그라운드 실행
```

---

### 3-4. 트레이 앱 (`core/tray.py`)

시스템 트레이에 아이콘을 표시하고 사용자 제어를 제공하는 모듈.

#### 동작

| 동작 | 설명 |
|------|------|
| 부팅 시 자동 상주 | 트레이에 파란 "B" 아이콘 표시 |
| 우클릭 → 대시보드 열기 | 기본 브라우저로 `http://127.0.0.1:8000` 오픈 |
| 우클릭 → 종료 | 서버(uvicorn) + 트레이 프로세스 전체 종료 |

#### 아이콘 생성

Pillow로 런타임에 생성. 파란 원(#2563EB) + 흰색 "B" 텍스트. 외부 이미지 파일 불필요.

---

### 3-5. REST API (`api/server.py`)

대시보드(React)와 통신하기 위한 FastAPI 서버.  
`127.0.0.1:8000`에서 실행되며 모바일 UA는 차단(리다이렉트)한다.

#### 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/items` | 시작 항목 전체 조회 |
| `POST` | `/api/items` | 항목 추가 |
| `PATCH` | `/api/items/{id}` | 항목 수정 |
| `DELETE` | `/api/items/{id}` | 항목 삭제 |
| `POST` | `/api/items/{id}/toggle` | 활성화/비활성화 토글 |
| `POST` | `/api/items/{id}/run` | 특정 항목 즉시 실행 |
| `GET` | `/api/settings` | 전체 설정 조회 |
| `PATCH` | `/api/settings` | 설정 수정 |
| `POST` | `/api/startup/register` | 시작 프로그램 등록 |
| `POST` | `/api/startup/unregister` | 시작 프로그램 해제 |
| `GET` | `/api/apps/search` | 설치된 앱 검색 |
| `GET` | `/api/browsers` | 사용 가능한 브라우저 목록 |
| `GET` | `/` | React 대시보드 (정적 파일 서빙) |

---

### 3-6. 진입점 (`main.py`)

| 실행 명령 | 동작 |
|----------|------|
| `python main.py` | **기본 모드**: 트레이 아이콘 상주 + 서버 시작 + 시작 항목 실행 (부팅 시 자동 호출) |
| `python main.py --serve` | **서버 모드**: FastAPI 서버 실행 + 브라우저 자동 오픈 (개발·수동 관리용) |
| `python main.py --register` | Windows 시작 프로그램에 등록 |
| `python main.py --unregister` | Windows 시작 프로그램에서 해제 |
| `python main.py --status` | 현재 등록 상태 출력 |

---

## 4. 사용 기술

### 현재

| 기술 | 버전 | 용도 |
|------|------|------|
| Python | 3.11+ | 전체 런타임 |
| FastAPI | 0.111+ | REST API 서버 |
| Uvicorn | 0.29+ | ASGI 서버 (FastAPI 구동) |
| pystray | 0.19+ | 시스템 트레이 아이콘 |
| Pillow | 10.0+ | 트레이 아이콘 이미지 생성 |
| psutil | 5.9+ | 프로세스 실행 중 여부 확인 |
| `subprocess` | 표준 라이브러리 | 앱·exe 실행 |
| `threading` | 표준 라이브러리 | delay 병렬 처리, 서버·트레이 분리 |
| `winreg` | 표준 라이브러리 (Windows 내장) | 레지스트리 읽기/쓰기 |
| `webbrowser` | 표준 라이브러리 | 대시보드 브라우저 오픈 |
| `logging` | 표준 라이브러리 | 실행 로그 기록 |
| `json` | 표준 라이브러리 | config.json 파싱 |
| `uuid` | 표준 라이브러리 | 항목 ID 자동 생성 |
| `pathlib` | 표준 라이브러리 | 경로 처리 |
| PyInstaller | 6.0+ | 단일 디렉터리 .exe 패키징 |

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
[B-Handless.exe 실행] (콘솔 창 없음)
      │
      ▼
[main.py — 기본 모드]
      │
      ├─ Thread: launch_all(config)
      │     ├── enabled=true 항목 필터링
      │     └── 각 항목 → delay 후 Popen
      │           ├── [browser_url] → Edge/브라우저 → {url}
      │           ├── [exe / app]   → Popen({path})
      │           └── [uploaded_exe]→ uploads/ → Popen({path})
      │
      ├─ Thread (daemon): uvicorn
      │     └── FastAPI 127.0.0.1:8000
      │           └── server/web/ 정적 파일 서빙 (PWA)
      │
      └─ Main Thread: pystray
            └── 🔵 트레이 아이콘 상주
```

### 시작 프로그램 등록/해제 플로우

```
[대시보드 설정 페이지에서 '시작 프로그램 등록' 토글]
      │
      ▼
[FastAPI POST /api/startup/register 또는 /api/startup/unregister]
      │
      ├── register → scheduler.register()
      │       └── winreg SetValueEx → HKCU\...\Run 에 실행 명령어 기록
      │
      └── unregister → scheduler.unregister()
              └── winreg DeleteValue → HKCU\...\Run 에서 항목 제거
```

---

## 6. 디렉토리 구조

```
server/
│
├── main.py                # 진입점 (기본: 트레이 앱 / --serve: 서버+브라우저)
├── b-handless.spec        # PyInstaller 패키징 스펙
├── config.json            # 시작 항목 및 설정 (런타임 생성, gitignore)
├── requirements.txt       # 패키지 목록
├── .gitignore
│
├── core/
│   ├── __init__.py
│   ├── launcher.py        # 실행 엔진 (앱·URL·exe 실행)
│   ├── config_manager.py  # config.json CRUD
│   ├── scheduler.py       # Windows 레지스트리 제어
│   ├── security.py        # 경로·URL 검증, 브라우저 화이트리스트
│   └── tray.py            # 시스템 트레이 아이콘 (pystray + Pillow)
│
├── api/
│   ├── __init__.py
│   └── server.py          # FastAPI 앱 (/api prefix + 정적 서빙)
│
├── web/                   # React 빌드 결과물 (build.bat으로 생성, gitignore)
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

**exe / app / uploaded_exe**
```json
{
  "path": "C:/path/to/app.exe",
  "args": ["--flag", "value"]
}
```

### settings 필드

| 필드 | 기본값 | 설명 |
|------|--------|------|
| `api_port` | 8000 | FastAPI 서버 포트 |
| `dashboard_port` | 3000 | React 개발 서버 포트 |
| `log_enabled` | true | 로그 기록 여부 |
| `registered_as_startup` | false | Windows 시작 프로그램 등록 상태 |

---

## 8. 설치 및 실행

### 개발 모드

```bash
# 서버 (트레이 + 서버 + 시작 항목)
cd server
python main.py

# 서버만 (브라우저 자동 오픈)
python main.py --serve

# 프론트엔드 개발 서버 (포트 3000, API 프록시 → 8000)
cd dashboard
npm run dev
```

### 패키징 (배포 빌드)

```bash
build.bat     # React 빌드 → server/web 복사 → PyInstaller 패키징
install.bat   # AppData\Local\B-Handless 설치 + 시작 프로그램 등록
```

설치 후 재부팅하면 트레이 아이콘이 자동으로 나타난다.

### PWA로 설치 (앱처럼 사용)

1. `B-Handless.exe` 실행 (또는 `python main.py`)
2. 브라우저에서 `http://127.0.0.1:8000` 접속
3. 주소창 오른쪽 **앱으로 설치** 아이콘 클릭
4. 설치 후 바탕화면/시작 메뉴에서 앱 아이콘으로 실행

### 시작 프로그램 수동 제어

```bash
python main.py --register    # 시작 프로그램 등록
python main.py --unregister  # 해제
python main.py --status      # 등록 상태 확인
```

---

## 개발 현황

| Phase | 내용 | 상태 |
|-------|------|------|
| Phase 1 | Python 핵심 엔진 (launcher, config, scheduler) | 완료 |
| Phase 2 | 보안 강화 (경로·URL 검증, SHA-256 무결성) | 완료 |
| Phase 3 | FastAPI REST API 서버 | 완료 |
| Phase 4 | React 대시보드 (PWA, 매트 파스텔톤 UI) | 완료 |
| Phase 5 | PyInstaller .exe 패키징 + 설치 자동화 | 완료 |
| Phase 6 | 시스템 트레이 앱 (pystray) — 부팅 시 서버 자동 시작 | 완료 |
