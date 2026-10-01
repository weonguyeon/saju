# saju — 별하(Byeolha) 사주풀이

Flask 웹앱. 사주 계산(`saju_logic.py`) + AI 장문 해석(`ai_analysis.py`). 명세 문서 01~07, 프로젝트 규칙 `.agent/rules/project_rules.md`(한국어 주석·PEP 8).

## 실행
- `.venv/bin/python -c "from app import app; app.run(port=5050)"` → http://127.0.0.1:5050 (맥 5000번은 AirPlay 점유)
- AI 백엔드: `AI_BACKEND=claude`(기본, 로그인된 `claude` CLI 구독·키 불필요) / `openai`(`OPENAI_API_KEY` 필요)
- 선택 환경변수: `CLAUDE_MODEL`(비우면 CLI 기본), `CLAUDE_BIN`, `CLAUDE_TIMEOUT`(기본 600초)

## 주의
- Claude 호출은 `claude -p --tools "" --setting-sources "" --strict-mcp-config`를 빈 임시 폴더에서 실행 — 도구·훅·CLAUDE.md가 섞이지 않게 한 것이니 유지.
- `--bare`는 OAuth를 안 읽어(API 키 전용) 구독 로그인으로는 못 쓴다.
- 분석 1회 약 2분 소요(동기 요청). gunicorn 배포 시 워커 timeout을 늘려야 한다.
- 알려진 버그: `app.py`의 `current_daewun`이 나이와 무관하게 첫 대운(`daewoon[0]`)을 넘긴다.
