# B-Handless 서비스 흐름

> 프로젝트 실제 동작 순서와 구성 요소 문서입니다.

---

## 핵심 개념

| 개념 | 설명 |
|------|------|
| **B-Handless 프로세스** | `pythonw.exe main.py` 또는 패키징된 `.exe`. 부팅 시 자동 실행되는 주체 |
| **대시보드 서버** | `--serve` 모드에서만 실행되는 FastAPI + uvicorn (포트 8000). 부팅 자동 실행에는 포함되지 않음 |
| **config.json** | 실행할 항목 목록과 설정을 저장하는 로컬 파일. 레지스트리와 무관 |
| **레지스트리 Run 키** | Windows 로그인 시 자동으로 프로그램을 실행시키는 레지스트리 위치 |

---

## 레지스트리에 등록되는 것

```
HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
└─ B-Handless = "C:\...\pythonw.exe" "C:\...\main.py"
               (또는 패키징된 경우: "C:\...\B-Handless.exe")
```

- 등록되는 항목: **B-Handless 프로그램 자체 1개**
- 등록된 웹/앱/실행파일들은 레지스트리에 추가 등록되지 않음
- `--serve` 명령은 레지스트리를 전혀 변경하지 않음
- 등록/해제는 `--register` / `--unregister` CLI 명령으로만 가능

---

## 흐름 1 — 최초 설치 및 설정

```
1. python main.py --serve 실행
   │
   ├─ FastAPI 서버 시작 (127.0.0.1:8000)
   └─ 브라우저 자동 오픈 (1.5초 후)

2. 터미널에서 시작 프로그램 등록
   │
   └─ python main.py --register
      │
      └─ 레지스트리 Run 키에 B-Handless 등록
         대시보드 설정 페이지에서 ✅ 등록됨 표시

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
      └─ "B-Handless" 항목 발견 → pythonw.exe main.py 실행
         (콘솔 창 없이 백그라운드 실행)
         │
         └─ main.py 시작
            │
            ├─ config.json 로드
            ├─ enabled=true 인 항목만 필터링
            │
            └─ launch_all(config) 호출
               │
               ├─ 항목마다 독립 스레드 생성 (daemon=False)
               │
               ├─ [delay=0]  즉시 subprocess.Popen([경로, ...args]) 실행
               ├─ [delay=5]  5초 sleep 후 subprocess.Popen 실행
               └─ [delay=30] 30초 sleep 후 subprocess.Popen 실행
               │
               │  ※ subprocess.Popen: 레지스트리 등록 없이 경로 직접 실행
               │  ※ 실행된 앱(Chrome 등)은 독립 프로세스로 분리됨
               │
               └─ 모든 스레드 join() — 가장 긴 딜레이 항목 완료까지 대기
                  │
                  └─ launch_all 반환
                     │
                     └─ main.py 프로세스 자동 종료
                        ├─ 포트 열리지 않음
                        └─ 백그라운드 프로세스 없음
```

---

## 흐름 3 — 대시보드 수동 접속 (항목 관리)

```
python main.py --serve 수동 실행
   │
   ├─ FastAPI 서버 시작 (127.0.0.1:8000)
   │   └─ 레지스트리 변경 없음
   │
   └─ 브라우저 자동 오픈
      │
      ├─ 항목 추가 / 수정 / 삭제 → config.json 반영
      ├─ "지금 실행" 버튼 → POST /api/items/{id}/run
      │   └─ launch_by_id() → subprocess.Popen 즉시 실행
      │
      └─ 작업 완료 후 Ctrl+C 또는 창 닫기 → 서버 종료
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

```
server/
├─ config.json          ← 실행 항목 목록 + 설정 (레포 미포함, .gitignore)
├─ config.json.hash     ← SHA-256 무결성 검증 파일 (레포 미포함)
├─ uploads/             ← 업로드된 실행파일 (레포 미포함, .gitkeep만 포함)
└─ logs/startup.log     ← 실행 로그 (레포 미포함)
```

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
| `python main.py` | 항목 전체 실행 후 종료 | 없음 |
| `python main.py --serve` | 대시보드 서버 실행 (수동 관리용) | 없음 |
| `python main.py --register` | Windows 시작 프로그램 등록 | Run 키 추가 |
| `python main.py --unregister` | Windows 시작 프로그램 해제 | Run 키 삭제 |
| `python main.py --status` | 등록 상태 확인 | 없음 |

---

_마지막 업데이트: 2026-05-06_
