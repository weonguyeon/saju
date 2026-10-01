# 원구연-무료 사주풀이

생년월일과 태어난 시간으로 사주 원국·오행·십성·대운·세운을 계산하고, AI가 풀이를 덧붙이는 무료 웹 서비스입니다.
운영 주소: https://lab2.shumong.co.kr

## 주요 기능

- **절기 기준 만세력**: 입춘·절입 시각을 분 단위로 비교해 연·월주를 정합니다 (`lunar_python`).
- **한국 시간 보정**: 출생지 경도(지방평균태양시), 1954~61년 UTC+8:30, 서머타임(1948~60·1987~88년)을 IANA 시간대 DB로 자동 반영합니다. 끌 수 있습니다.
- **입력**: 양력/음력(윤달), 시간 모름(시주 제외), 출생 지역, 자시 처리(야자시/다음날).
- **원국표**: 시·일·월·연 순, 천간·지지 한자 타일(오행 색), 십성, 지장간(여기·중기·정기), 12운성.
- **분포**: 오행·십성 막대, 일간을 돕는/빼는 기운 비교.
- **대운·세운**: 실제 대운수(만 나이)와 순행/역행, 가로 카드에서 고르면 그 10년의 세운 표가 바뀝니다.
- **AI 풀이**: 총평·성향·재물·일·애정·건강·근묘화실·대운 흐름. 4묶음으로 나눠 동시에 생성하고, 결과 화면은 바로 띄운 뒤 오는 대로 채웁니다. 같은 입력은 캐시로 즉시 보여줍니다.
- **계산 기준 표기**: 보정 시각·시간대·대운 기준을 결과 하단에 밝힙니다.
- **자미두수 명반** (탭): 12궁 4×4 명반, 주성 14개·밝기·사화·보좌성, 대한(세는나이), 주요 궁 읽기. iztro-py(MIT). 시진은 시주와 같은 보정 시각.
- **별자리 출생차트** (탭): 태양·달·상승궁, 원형 차트(SVG), 행성 10개 위치·하우스(Placidus, 극지는 Whole Sign)·역행, 애스펙트, 원소 분포. astronomy-engine(MIT) + 자체 하우스 계산 — Swiss Ephemeris 값과 0.01° 이내로 테스트.
- **택일·구성** (탭): 본명성·월명성(입춘 기준), 목적별 길일(이사·결혼·개업·계약: 宜·황도·띠 충 제외), 30일 달력(손없는날·황도·건제·충). lunar_python.
- **세 가지 비교** (탭): 사주·자미두수·출생차트 AI 교차 분석. 버튼을 눌렀을 때만 생성.
- **보류한 체계**: 기문둔갑(쓸 만한 Python 구현 kinqimen 에 라이선스 파일 없음), 육효(한국어 괘사 자유 라이선스 데이터 미검수) — 질문 시점 기반이라 별도 기능으로 검토.

## 빠른 시작

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
PORT=5050 .venv/bin/python app.py      # http://127.0.0.1:5050  (맥 5000번은 AirPlay 점유)
.venv/bin/python -m pytest -q tests    # 테스트
```

AI 연결은 기본으로 로그인된 Claude Code CLI(`claude -p`)를 씁니다. 환경변수:

| 변수 | 기본값 | 설명 |
|---|---|---|
| `AI_BACKEND` | `claude` | `openai`면 `OPENAI_API_KEY`로 GPT-4o |
| `CLAUDE_MODEL` | `sonnet` | 실측: sonnet 약 18초 / opus 약 33초 / haiku 약 91초 (4묶음 병렬, 전체 완료 기준) |
| `CLAUDE_BIN`, `CLAUDE_TIMEOUT` | PATH의 `claude`, 100초 | |
| `AI_SLOT_WAIT` | 20초 | 동시 실행 자리가 없을 때 기다리는 시간. 넘으면 503 후 화면이 자동 재시도 |
| `AI_MAX_CONCURRENCY` | 8 | 동시에 도는 claude 프로세스 상한 |
| `RATE_LIMIT_PER_IP`, `RATE_LIMIT_TOTAL` | 5, 200 | 외부 방문자 하루 AI 풀이 횟수(IPv6는 /64 단위). 캐시 적중은 차감 안 함 |
| `TRUST_LOCAL_UNLIMITED` | 1 | 1이면 헤더 없는 로컬 접속은 무제한. 운영(plist)은 0 |

## 구조

```
app.py            라우트·입력 검증·화면용 데이터·사용량 제한
saju_logic.py     만세력 계산 (절기·시간대·대운·지장간·12운성)
ziwei_logic.py    자미두수 명반 (iztro-py 감싸기)
western_logic.py  출생차트 (행성·ASC/MC·하우스·애스펙트·원형 차트 좌표)
almanac_logic.py  구성학·택일 (lunar_python, 宜忌 한국어 매핑 114개)
ai_analysis.py    AI 풀이 (4묶음 병렬·캐시·동시 실행 제한)
templates/        base / index / result (+ _ziwei/_natal/_almanac/_cross 탭, licenses)
static/style.css  라이트·다크 토큰, 오행 색(대비 4.5:1 이상)
tests/            계산·앱·AI 모듈 테스트
deploy/, scripts/ 맥미니 launchd·배포 스크립트
```

`01_`~`07_` 명세 문서는 처음 받은 코드 기준의 초기 문서라 현재 코드와 다릅니다.

## 배포 (맥미니)

```bash
bash scripts/setup-mini.sh    # 최초 1회: 클론·venv·launchd(ai.saju.lab2, 127.0.0.1:4510)·터널 호스트
bash scripts/deploy-mini.sh   # 이후: push된 main을 pull·재시작하고 배포 커밋 대조
```

DNS는 Cloudflare 대시보드에서 `lab2` CNAME → `<터널ID>.cfargotunnel.com`(프록시 켬)을 직접 추가합니다.

## 주의

- 풀이는 재미와 자기 성찰을 위한 참고 자료입니다.
- Anthropic 문서상 Free/Pro/Max 구독 로그인으로 다른 사용자 요청을 처리하는 것은 허용되지 않습니다. 공개 운영을 이어가려면 `AI_BACKEND`를 API 키 방식으로 바꾸는 것을 권장합니다.
