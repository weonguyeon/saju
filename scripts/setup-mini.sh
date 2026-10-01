#!/bin/bash
# 맥미니 최초 설치 — 클론·가상환경·launchd 등록·터널 호스트 추가. 한 번만 실행한다.
# 사용: bash scripts/setup-mini.sh
# 사람이 할 일: Cloudflare 대시보드(shumong.co.kr 존) → DNS → CNAME  lab2 → <터널ID>.cfargotunnel.com (프록시 켬)
#   `cloudflared tunnel route dns` 는 쓰지 않는다 — 인증서가 junglefutures.com 존에 묶여 엉뚱한 레코드를 만든다.
set -euo pipefail
MINI="kukumac@172.30.1.57"
HOST="lab2.shumong.co.kr"
PORT=4510

ssh -o BatchMode=yes "$MINI" "HOST='$HOST' PORT='$PORT' bash -s" <<'REMOTE'
set -euo pipefail
cd ~/Developer
[ -d saju ] || git clone -q https://github.com/weonguyeon/saju.git
cd saju
git pull -q --ff-only
[ -x .venv/bin/python ] || ~/.local/share/mise/installs/python/3.13.5/bin/python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip >/dev/null
.venv/bin/pip install -q -r requirements.txt

PL=~/Library/LaunchAgents/ai.saju.lab2.plist
cp deploy/ai.saju.lab2.plist "$PL"
launchctl bootout gui/$(id -u)/ai.saju.lab2 2>/dev/null || true
for i in $(seq 1 30); do launchctl print gui/$(id -u)/ai.saju.lab2 >/dev/null 2>&1 || break; sleep 1; done
launchctl bootstrap gui/$(id -u) "$PL"

CFG=~/.cloudflared/config.yml
if grep -q "hostname: $HOST\$" "$CFG"; then
  echo "ingress 에 $HOST 이미 있음"
else
  # 임시 파일에 고친 뒤 검증을 통과해야만 교체한다 (공유 터널이 깨진 설정을 읽지 않도록)
  BAK="$CFG.bak-$(date +%Y%m%d-%H%M)-saju"
  TMP="$CFG.tmp-saju"
  cp "$CFG" "$BAK"
  /usr/bin/python3 - "$CFG" "$TMP" "$HOST" "$PORT" <<'PY'
import sys
src, dst, host, port = sys.argv[1:5]
s = open(src).read()
anchor = "  - service: http_status:404"
assert s.count(anchor) == 1, "catch-all 줄을 정확히 1개 찾지 못했다"
add = f"  # 원구연-무료 사주풀이 (saju, {port})\n  - hostname: {host}\n    service: http://localhost:{port}\n"
open(dst, "w").write(s.replace(anchor, add + anchor))
PY
  if /opt/homebrew/bin/cloudflared tunnel --config "$TMP" ingress validate; then
    mv "$TMP" "$CFG"
    launchctl kickstart -k gui/$(id -u)/ai.axcampus.tunnel
  else
    rm -f "$TMP"; echo "❌ 터널 설정 검증 실패 — 원래 설정 유지"; exit 1
  fi
fi
/opt/homebrew/bin/cloudflared tunnel ingress rule "https://$HOST/" | tail -2
UP=0
for i in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:$PORT/healthz"; then UP=1; break; fi
  sleep 1
done
echo
[ "$UP" = "1" ] || { echo "❌ 앱이 뜨지 않음"; tail -20 ~/Library/Logs/saju-lab2.err.log; exit 1; }
grep '^tunnel:' "$CFG"
REMOTE
