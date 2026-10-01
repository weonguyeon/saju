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
launchctl bootstrap gui/$(id -u) "$PL"

CFG=~/.cloudflared/config.yml
if grep -q "hostname: $HOST\$" "$CFG"; then
  echo "ingress 에 $HOST 이미 있음"
else
  cp "$CFG" "$CFG.bak-$(date +%Y%m%d-%H%M)-saju"
  /usr/bin/python3 - "$CFG" "$HOST" "$PORT" <<'PY'
import sys
p, host, port = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(p).read()
anchor = "  - service: http_status:404"
assert s.count(anchor) == 1, "catch-all 줄을 정확히 1개 찾지 못했다"
add = f"  # 원구연-무료 사주풀이 (saju, {port})\n  - hostname: {host}\n    service: http://localhost:{port}\n"
open(p, "w").write(s.replace(anchor, add + anchor))
PY
  /opt/homebrew/bin/cloudflared tunnel ingress validate
  launchctl kickstart -k gui/$(id -u)/ai.axcampus.tunnel
fi
/opt/homebrew/bin/cloudflared tunnel ingress rule "https://$HOST/" | tail -2
for i in $(seq 1 30); do
  curl -sf "http://127.0.0.1:$PORT/healthz" && break; sleep 1
done
echo
grep '^tunnel:' "$CFG"
REMOTE
