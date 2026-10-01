# saju — 원구연-무료 사주풀이

Flask 웹앱. 만세력 계산(`saju_logic.py`) + AI 풀이(`ai_analysis.py`). 운영 https://lab2.shumong.co.kr (맥미니 launchd `ai.saju.lab2`, 127.0.0.1:4510, axcampus 터널). 프로젝트 규칙 `.agent/rules/project_rules.md`(한국어 주석·PEP 8). 공개 레포.

## 실행·검증
- `PORT=5050 .venv/bin/python app.py` (맥 5000번은 AirPlay 점유)
- `.venv/bin/python -m pytest -q tests` — 계산·앱·AI 모듈 테스트. 화면 변경 시 Playwright로 375px `scrollWidth` 실측.
- 배포: `bash scripts/deploy-mini.sh` (커밋·push 안 됐으면 거부, 실행 중 프로세스의 `/healthz` sha 대조). 최초 설치는 `scripts/setup-mini.sh`. 개발 의존성은 `requirements-dev.txt`, 운영은 버전 고정 `requirements.txt`.

## 계산 규칙 (바꾸면 테스트부터)
- 연·월주 = lunar_python 절기(북경시 기준) — 입력 한국 시각을 UTC로 바꾼 뒤 +8시간으로 비교. 일·시주 = 보정 시 UTC + 경도×4분(지방평균태양시), 아니면 입력 시각.
- 시간대 이력(UTC+8:30 시기, 서머타임)은 `ZoneInfo("Asia/Seoul")`가 처리. 직접 표를 만들지 말 것.
- 지장간은 국내 표(`HIDDEN_STEMS`) — lunar_python의 중국식 표(자=계 하나)를 쓰지 않는다.
- 대운 나이는 만 나이(시작일 기준). lunar_python의 나이(虚岁)를 그대로 쓰지 않는다.

## AI
- `claude -p --tools "" --setting-sources "" --strict-mcp-config`를 빈 임시 폴더에서 실행 — 도구·훅·CLAUDE.md가 섞이지 않게 한 것이니 유지. `--bare`는 OAuth를 안 읽어 구독 로그인으로는 못 쓴다.
- 4묶음(summary/life/daewoon/domains) 병렬, 결과 화면은 즉시 렌더 후 `/api/analysis/<id>/<group>`로 채움. 기본 모델 sonnet.
- 캐시·분석 ID·사용량 카운터가 프로세스 메모리에 있다 → gunicorn 워커는 1개(스레드로 동시 처리). 재시작하면 초기화.
- 사용량 제한: 외부(CF-Connecting-IP) 방문자 IP(IPv6는 /64)당 하루 5회·전체 200회, 캐시 적중은 차감 안 함. 분석 ID 하나로 묶음마다 3회까지만 시도(실패 재호출 무한 반복 방지).
- 시간 예산: 슬롯 대기 20초 + claude 100초 < Cloudflare 응답 제한 125초. 늘리면 524가 난다.
- claude -p 맥락에 **로그인 계정 이메일이 들어간다**(개인 CLAUDE.md는 안 들어감, 2026-10-01 실측) → `scrub()`이 출력의 이메일·IP·로컬 경로를 지운다. 이름 칸은 글자·공백만 허용. 둘 다 유지.
- ⚠️ 공개 서비스에 구독 CLI를 쓰는 것은 Anthropic 문서상 허용되지 않는 방식(사용자가 위험 안내 후 선택, 2026-10-01). API 키 전환은 `AI_BACKEND`로.
