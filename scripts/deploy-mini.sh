#!/bin/bash
# 맥미니 배포 — push된 main을 미니에서 pull·의존성 설치·재시작하고 배포 커밋을 대조한다.
# 사용: bash scripts/deploy-mini.sh   (DOMAIN="" 이면 도메인 검사 생략)
set -u
MINI="kukumac@172.30.1.57"
BRANCH=main
PORT=4510
DOMAIN="${DOMAIN-https://lab2.shumong.co.kr}"

# 커밋만 하고 push 안 한 채 배포하면 미니는 옛 코드를 띄운다 — push 안 된 커밋이 있으면 거부
if [ -n "$(git status --porcelain)" ]; then
  echo "❌ 커밋 안 된 변경이 있다. 커밋부터 하라."; git status --short | head; exit 1
fi
git fetch -q origin || { echo "❌ fetch 실패"; exit 1; }
AHEAD=$(git rev-list --count "origin/$BRANCH..$BRANCH")
[ "$AHEAD" = "0" ] || { echo "❌ push 안 된 커밋 ${AHEAD}개. 커밋과 push 는 한 세트다."; exit 1; }
WANT_SHA=$(git rev-parse "origin/$BRANCH")
echo "배포 대상 $BRANCH ${WANT_SHA:0:7}"

OUT=$(ssh -o BatchMode=yes "$MINI" "PORT=$PORT bash -s" <<'REMOTE'
set -euo pipefail
cd ~/Developer/saju
git pull -q --ff-only
.venv/bin/pip install -q -r requirements.txt || { echo "PIP_FAILED"; exit 23; }
CLAUDE_BIN=$(/usr/bin/plutil -extract EnvironmentVariables.CLAUDE_BIN raw deploy/ai.saju.lab2.plist)
"$CLAUDE_BIN" --version >/dev/null || { echo "CLAUDE_MISSING $CLAUDE_BIN"; exit 24; }
cp deploy/ai.saju.lab2.plist ~/Library/LaunchAgents/ai.saju.lab2.plist
launchctl bootout gui/$(id -u)/ai.saju.lab2 2>/dev/null || true
# 옛 프로세스가 포트를 놓을 때까지 기다린다 (안 그러면 옛 프로세스의 healthz를 새 것으로 착각)
for i in $(seq 1 60); do lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1 || break; sleep 1; done
lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1 && { echo "PORT_BUSY"; exit 25; }
# bootout은 비동기라 서비스 등록이 완전히 풀린 뒤 등록한다 (안 그러면 "Bootstrap failed: 5")
for i in $(seq 1 30); do launchctl print gui/$(id -u)/ai.saju.lab2 >/dev/null 2>&1 || break; sleep 1; done
OK=0
for i in 1 2 3 4 5; do
  if launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.saju.lab2.plist 2>/dev/null; then OK=1; break; fi
  sleep 2
done
[ "$OK" = "1" ] || { echo "BOOTSTRAP_FAILED"; exit 26; }
UP=0
for i in $(seq 1 30); do
  if [ "$(curl -s -o /dev/null -w %{http_code} http://127.0.0.1:$PORT/healthz)" = "200" ]; then UP=1; break; fi
  sleep 1
done
[ "$UP" = "1" ] || { echo "APP_NOT_UP"; tail -20 ~/Library/Logs/saju-lab2.err.log; exit 22; }
echo "HEALTH=$(curl -s http://127.0.0.1:$PORT/healthz)"
echo "INDEX=$(curl -s -o /dev/null -w %{http_code} http://127.0.0.1:$PORT/)"
curl -s http://127.0.0.1:$PORT/healthz | /usr/bin/python3 -c 'import json,sys; print("DEPLOYED_SHA=" + (json.load(sys.stdin).get("sha") or ""))'
REMOTE
) || { echo "$OUT"; echo "❌ 원격 배포 실패"; exit 1; }

echo "$OUT" | grep -v '^DEPLOYED_SHA='
pick() { echo "$OUT" | sed -n "s/^$1=//p" | tail -1; }
[ "$(pick INDEX)" = "200" ] || { echo "❌ 첫 화면 응답 $(pick INDEX)"; exit 1; }
case "$(pick HEALTH)" in *'"ai":true'*) ;; *) echo "❌ AI 사용 불가 상태: $(pick HEALTH)"; exit 1 ;; esac
GOT=$(pick DEPLOYED_SHA)
[ "$GOT" = "$WANT_SHA" ] || { echo "❌ 미니 커밋 불일치 기대 ${WANT_SHA:0:7} / 실제 ${GOT:0:7}"; exit 1; }
echo "✅ 배포 커밋 일치 ${GOT:0:7}"

if [ -n "$DOMAIN" ]; then
  echo "domain $(curl -s -o /dev/null -w %{http_code} --max-time 20 "$DOMAIN/healthz")"
fi
