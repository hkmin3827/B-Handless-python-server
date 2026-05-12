# B-Handless 서비스 흐름

> 프로젝트 실제 동작 순서와 구성 요소 문서입니다.

---

## 핵심 개념

| 개념 | 설명 |
|------|------|
| **B-Handless 프로세스** | `B-Handless.exe` 또는 `pythonw.exe main.py`. 부팅 시 트레이 아이콘으로 상주하는 주 프로세스. 서버 시작·시작 항목 실행 포함 |
| **트레이 아이콘** | 시스템 트레이에 상주하는 파란 "B" 아이콘. 대시보드 열기·종료를 우클릭 메뉴로 제어 |
| **대시보드 서버** | 기본 모드 실행 시 자동으로 시작되는 FastAPI + uvicorn (포트 8000). `server/web/` 정적 파일 서빙 포함 |
| **config.json** | 실행할 항목 목록과 설정을 저장하는 로컬 파일. 레지스트리와 무관 |
| **레지스트리 Run 키** | Windows 로그인 시 자동으로 프로그램을 실행시키는 레지스트리 위치 |

---

## 레지스트리에 등록되는 것

```
[시작 프로그램]
HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
└─ B-Handless = "C:\...\B-Handless.exe"
               (개발 환경: "C:\...\pythonw.exe" "C:\...\main.py")

[URL 프로토콜 핸들러]
HKEY_CURRENT_USER\SOFTWARE\Classes\bhandless
└─ shell\open\command = "C:\...\B-Handless.exe" "%1"
```

- 등록되는 항목: **B-Handless 프로그램 자체 1개** (시작 프로그램)
- **bhandless://** 프로토콜: PWA 오프라인 배너에서 서버 재시작 링크용
- 등록된 웹/앱/실행파일들은 레지스트리에 추가 등록되지 않음
- `--serve` 명령은 레지스트리를 전혀 변경하지 않음
- 시작 프로그램 등록/해제: `--register` / `--unregister`
- 프로토콜 등록/해제: `--protocol-register` / `--protocol-unregister`

---

## 흐름 1 — 최초 설치 및 설정

```
1. install.bat 실행
   │
   ├─ [1/4] AppData\Local\B-Handless\ 에 파일 복사
   ├─ [2/4] config.json 설치 디렉토리에 복사
   ├─ [3/4] B-Handless.exe --register 자동 호출
   │          └─ Run 키에 B-Handless 등록 + config.json registered_as_startup=true
   └─ [4/4] B-Handless.exe --protocol-register 자동 호출
              └─ HKCU\SOFTWARE\Classes\bhandless 등록 (PWA 오프라인 재시작용)

2. 대시보드 접속 (B-Handless.exe 실행 후)
   │
   └─ 트레이 아이콘 우클릭 → "대시보드 열기"
      또는 브라우저에서 http://127.0.0.1:8000 직접 접속

3. 대시보드에서 실행 항목 추가
   │
   ├─ 웹 URL: URL + 브라우저 선택
   ├─ 앱:     .exe / .lnk 경로 또는 앱 검색으로 선택
   └─ 실행파일: .exe / .bat / .cmd 경로
   │
   └─ POST /api/items → server/config.json 에 저장
                        (레지스트리 등록 없음)
```

---

## 흐름 2 — 부팅 시 자동 실행 (핵심 흐름)

```
Windows 로그인
   │
   └─ 레지스트리 Run 키 읽기
      └─ "B-Handless" 항목 발견
         → B-Handless.exe 실행 (콘솔 창 없음, console=False)
         │
         └─ main.py 시작 (인수 없음 = 기본 모드)
            │
            ├─ Thread (daemon=False): launch_all(config)
            │   │
            │   ├─ config.json 로드
            │   ├─ enabled=true 항목 필터링
            │   └─ 항목마다 독립 스레드 생성
            │       ├─ [delay=0]  즉시 subprocess.Popen 실행
            │       ├─ [delay=5]  5초 sleep 후 Popen 실행
            │       └─ [delay=30] 30초 sleep 후 Popen 실행
            │
            ├─ Thread (daemon=True): uvicorn 서버
            │   └─ FastAPI 시작 (127.0.0.1:8000)
            │       └─ server/web/ 정적 파일 서빙 (PWA 포함)
            │
            └─ Main Thread: pystray 트레이 아이콘 (블로킹)
                └─ 시스템 트레이에 🔵 "B" 아이콘 상주
                   ├─ 우클릭 "대시보드 열기" → webbrowser.open(127.0.0.1:8000)
                   └─ 우클릭 "B-Handless 종료"
                      → icon.stop() → 프로세스 종료
                         (daemon 스레드인 uvicorn도 함께 종료)
```

---

## 흐름 3 — 대시보드 수동 접속 (항목 관리)

```
[방법 A] 트레이 아이콘에서 열기 (기본 모드 실행 중일 때)
   │
   └─ 트레이 아이콘 우클릭 → "대시보드 열기"
      → 브라우저에서 http://127.0.0.1:8000 오픈

[방법 B] --serve 플래그로 수동 실행 (개발/디버그용)
   │
   └─ python main.py --serve
      ├─ FastAPI 서버 시작 (127.0.0.1:8000)
      └─ 브라우저 자동 오픈 (1.5초 후)
         │
         ├─ 항목 추가 / 수정 / 삭제 → config.json 반영
         ├─ "지금 실행" 버튼 → POST /api/items/{id}/run
         │   └─ launch_by_id() → subprocess.Popen 즉시 실행
         │
         └─ Ctrl+C 또는 창 닫기 → 서버 종료
```

---

## 실행 타입별 동작

| 타입 | 실행 방식 | 경로 예시 |
|------|-----------|-----------|
| `browser_url` | 레지스트리 App Paths에서 브라우저 경로 조회 후 `Popen` | `https://notion.so` |
| `app` | `subprocess.Popen([path])` 직접 실행 | `C:\...\KakaoTalk.exe` |
| `exe` | `subprocess.Popen([path, ...args])` 직접 실행 | `C:\...\script.bat` |
| `uploaded_exe` | uploads/ 폴더 내 파일 `Popen` 실행 | `uploads/my_tool/tool.exe` |

---

## 데이터 저장 구조

**개발 환경** (`python main.py`)
```
server/
├─ config.json          ← 실행 항목 목록 + 설정
├─ config.json.hash     ← SHA-256 무결성 검증 파일
├─ uploads/             ← 업로드된 실행파일
├─ web/                 ← React 빌드 결과물
└─ logs/startup.log     ← 실행 로그
```

**설치 환경** (`B-Handless.exe`, PyInstaller)
```
AppData\Local\B-Handless\
├─ B-Handless.exe       ← 실행 파일
├─ config.json          ← 실행 항목 목록 + 설정  ← exe 옆에 위치 (핵심)
├─ config.json.hash     ← SHA-256 무결성 검증 파일
├─ uploads/             ← 업로드된 실행파일
├─ logs/startup.log     ← 실행 로그
└─ _internal/           ← 앱 번들 (Python 런타임 등, 수정 불필요)
```

> `_internal/` 내부가 아닌 exe 옆에 데이터 파일을 두는 것이 핵심.  
> `core/config_manager.py`, `core/security.py`, `core/launcher.py` 는 `_app_root()` 함수로  
> frozen 환경과 개발 환경을 구분해 올바른 경로를 반환한다.

config.json 예시:
```json
{
  "startup_items": [
    {
      "id": "a1b2c3d4",
      "type": "browser_url",
      "label": "Notion",
      "enabled": true,
      "delay_seconds": 0,
      "url": "https://notion.so",
      "browser": "edge"
    },
    {
      "id": "e5f6g7h8",
      "type": "app",
      "label": "KakaoTalk",
      "enabled": true,
      "delay_seconds": 5,
      "path": "C:\\Program Files (x86)\\Kakao\\KakaoTalk\\KakaoTalk.exe"
    }
  ],
  "settings": {
    "api_port": 8000,
    "dashboard_port": 3000,
    "log_enabled": true,
    "registered_as_startup": true
  }
}
```

---

## CLI 명령 정리

| 명령 | 동작 | 레지스트리 변경 |
|------|------|----------------|
| `python main.py` | 트레이 앱 실행 (서버 + 시작 항목 + 트레이 아이콘) | 없음 |
| `python main.py --serve` | 서버 실행 + 브라우저 자동 오픈 (수동 관리·개발용) | 없음 |
| `python main.py --register` | Windows 시작 프로그램 등록 + config.json `registered_as_startup=true` | Run 키 추가 |
| `python main.py --unregister` | Windows 시작 프로그램 해제 | Run 키 삭제 |
| `python main.py --status` | 등록 상태 확인 | 없음 |
| `python main.py --protocol-register` | `bhandless://` URL 프로토콜 핸들러 등록 | `HKCU\SOFTWARE\Classes\bhandless` 추가 |
| `python main.py --protocol-unregister` | `bhandless://` URL 프로토콜 핸들러 해제 | 키 트리 삭제 |

---

---

## 흐름 4 — 서버 오프라인 시 재시작 (bhandless://)

PWA 앱 실행 시 서버가 꺼져 있으면 오프라인 배너가 표시된다.

```
[PWA 앱 열기]
   │
   └─ App.tsx 마운트 시 GET /api/items 헬스체크
      └─ 응답 없음 → "서버가 꺼져 있어요" 오버레이 표시
         │
         ├─ [서버 시작하기] 버튼 클릭
         │   └─ bhandless:// 링크 실행
         │       └─ 레지스트리 핸들러 → B-Handless.exe "bhandless://" 실행
         │           ├─ 서버 이미 실행 중 → 브라우저 열고 종료
         │           └─ 서버 꺼져 있음 → 트레이 앱 기본 모드로 시작
         │
         └─ [재연결 시도] 버튼 클릭
             └─ GET /api/items (cache: no-store) 재시도
                └─ 성공 시 → serverOnline=true, 오버레이 제거
```

---

_마지막 업데이트: 2026-05-12_
