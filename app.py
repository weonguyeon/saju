import os
import datetime
import secrets
import subprocess
import threading
import ipaddress
from collections import Counter, OrderedDict

from flask import Flask, render_template, request, jsonify, url_for

from saju_logic import SajuLogic, KST, REGIONS, DEFAULT_REGION, ELEMENT_KO, full_age
from ai_analysis import AIAnalysis, GROUPS, Busy

APP_TITLE = "원구연-무료 사주풀이"

app = Flask(__name__)
saju = SajuLogic()
ai = AIAnalysis()

GOD_GROUPS = [
    ('비겁', ['비견', '겁재'], '자존감, 경쟁, 동료'),
    ('식상', ['식신', '상관'], '표현, 재능, 활동'),
    ('재성', ['편재', '정재'], '재물, 현실 감각'),
    ('관성', ['편관', '정관'], '책임, 명예, 조직'),
    ('인성', ['편인', '정인'], '배움, 보호, 문서'),
]
ELEMENT_ORDER = ['wood', 'fire', 'earth', 'metal', 'water']


STEM_HANJA = dict(zip("갑을병정무기경신임계", "甲乙丙丁戊己庚辛壬癸"))
BRANCH_HANJA = dict(zip("자축인묘진사오미신유술해", "子丑寅卯辰巳午未申酉戌亥"))


@app.template_filter('hanja')
def hanja_filter(ko, kind='gan'):
    return (STEM_HANJA if kind == 'gan' else BRANCH_HANJA).get(ko, ko)


def _asset_version(name):
    # Cloudflare가 정적 파일에 4시간 캐시를 붙이므로, 내용이 바뀌면 주소(?v=)도 바뀌게 한다
    import hashlib
    with open(os.path.join(app.static_folder, name), 'rb') as f:
        return hashlib.sha1(f.read()).hexdigest()[:10]


ASSET_VER = {'style.css': _asset_version('style.css')}


@app.context_processor
def inject_globals():
    return {'app_title': APP_TITLE, 'regions': REGIONS, 'element_ko': ELEMENT_KO,
            'asset_url': lambda name: url_for('static', filename=name, v=ASSET_VER.get(name))}


# ----------------------------------------------------------------------
# 입력 검증
# ----------------------------------------------------------------------
class InputError(ValueError):
    def __init__(self, message, field=None):
        super().__init__(message)
        self.field = field  # 화면에서 빨간 테두리로 표시할 입력칸


def _int(src, key, label):
    try:
        return int(str(src.get(key, '')).strip())
    except ValueError:
        raise InputError(f"{label}을(를) 숫자로 입력해 주세요.", "date")


def _flag(src, key, default=False):
    v = src.get(key)
    if v is None:
        return default
    return v in ('1', 'on', 'true', True)


def parse_input(src):
    """폼/JSON 입력을 검증해 정리한다. 잘못된 값은 InputError"""
    name = ' '.join((src.get('name') or '').split())
    if not name:
        raise InputError("이름을 입력해 주세요.", "name")
    if len(name) > 20:
        raise InputError("이름은 20자 이내로 입력해 주세요.", "name")
    # 이름은 AI 프롬프트에 들어가므로 글자·공백·가운뎃점·하이픈만 받는다
    if not all(ch.isalpha() or ch in ' ·-' for ch in name):
        raise InputError("이름에는 글자와 띄어쓰기만 쓸 수 있습니다.", "name")

    gender = src.get('gender')
    if gender not in ('male', 'female'):
        raise InputError("성별을 선택해 주세요.")

    calendar = src.get('calendar') or 'solar'
    if calendar not in ('solar', 'lunar'):
        raise InputError("양력/음력을 선택해 주세요.")
    year, month, day = _int(src, 'year', '태어난 해'), _int(src, 'month', '태어난 월'), _int(src, 'day', '태어난 일')
    if not 1900 <= year <= 2100:
        raise InputError("태어난 해는 1900년부터 2100년 사이로 입력해 주세요.", "date")
    if not (1 <= month <= 12 and 1 <= day <= 31):
        raise InputError("존재하지 않는 날짜입니다. 생년월일을 확인해 주세요.", "date")
    leap = calendar == 'lunar' and _flag(src, 'leap')
    try:
        if calendar == 'lunar':
            birth_date = saju.lunar_to_solar(year, month, day, leap)
        else:
            birth_date = datetime.date(year, month, day)
    except ValueError as e:
        msg = str(e)
        raise InputError(msg if '음력' in msg else "존재하지 않는 날짜입니다. 생년월일을 확인해 주세요.", "date")

    time_unknown = _flag(src, 'time_unknown')
    if time_unknown:
        # 시간을 모르면 정오로 두고 시주는 화면·해석에서 뺀다
        birth_time = datetime.time(12, 0)
    else:
        try:
            birth_time = datetime.datetime.strptime((src.get('birth_time') or '').strip(), '%H:%M').time()
        except ValueError:
            raise InputError("태어난 시간을 입력하거나 '시간 모름'을 선택해 주세요.", "birth_time")

    birth = datetime.datetime.combine(birth_date, birth_time)
    if birth > datetime.datetime.now(KST).replace(tzinfo=None):
        raise InputError("아직 오지 않은 날짜입니다. 생년월일을 확인해 주세요.", "date")

    zishi = src.get('zishi') or 'split'
    if zishi not in ('split', 'next'):
        raise InputError("자시 처리 방식이 올바르지 않습니다.")
    region = src.get('region') or DEFAULT_REGION
    if region not in REGIONS:
        raise InputError("출생 지역이 올바르지 않습니다.")

    return {
        'name': name,
        'gender': gender,
        'calendar': calendar,
        'leap': leap,
        'input_ymd': (year, month, day),
        'birth': birth,
        'time_unknown': time_unknown,
        # 폼에서 온 요청(opts 표시)이면 체크박스가 꺼졌을 때 False, 그 밖에는 보정이 기본
        'solar_time': _flag(src, 'solar_time') if src.get('opts') else _flag(src, 'solar_time', default=True),
        'zishi': zishi,
        'region': region,
    }


# ----------------------------------------------------------------------
# 계산 → 화면용 데이터
# ----------------------------------------------------------------------
def _dw_label(dw):
    if not dw:
        return "대운 시작 전"
    return f"{dw['gan']}{dw['zhi']} 대운 ({dw['start_year']}~{dw['end_year']}, 만 {dw['age']}세~)"


def analyze(inp, today=None):
    """사주 계산 전체 (AI 제외). 템플릿·AI 프롬프트에 같이 쓰는 값을 돌려준다"""
    b = inp['birth']
    today = today or datetime.datetime.now(KST).date()
    pillars = saju.get_gan_zhi(b.year, b.month, b.day, b.hour, b.minute,
                               solar_time=inp['solar_time'], zishi=inp['zishi'], region=inp['region'])
    keys = ['year', 'month', 'day'] + ([] if inp['time_unknown'] else ['hour'])
    day_gan = pillars['day']['gan_idx']

    ohaeng = {e: 0 for e in ELEMENT_ORDER}
    for k in keys:
        ohaeng[pillars[k]['gan_element']] += 1
        ohaeng[pillars[k]['zhi_element']] += 1

    interp = saju.interpret(pillars, ohaeng, {'gender': inp['gender'], 'birth': b, 'today': today})
    if inp['time_unknown']:
        interp['ten_gods'].pop('hour', None)

    # 원국표 (시·일·월·연 순, 오른쪽에서 읽는 국내 관례)
    table = []
    for k, label in [('hour', '시주'), ('day', '일주'), ('month', '월주'), ('year', '연주')]:
        if k not in keys:
            table.append({'key': k, 'label': label, 'unknown': True})
            continue
        p = pillars[k]
        table.append({
            'key': k, 'label': label, 'unknown': False, 'pillar': p,
            'gan_god': interp['ten_gods'][k]['gan'],
            'zhi_god': interp['ten_gods'][k]['zhi'],
            'hidden': [{'gan': g, 'element': saju.STEM_OHAENG[saju.CHEONGAN.index(g)]} for g in saju.hidden_stems(p['zhi_idx'])],
            'stage': saju.twelve_stage(day_gan, p['zhi_idx']),
        })

    # 십성 분포 (일간 제외)
    counts = Counter()
    for k in keys:
        for pos in ('gan', 'zhi'):
            g = interp['ten_gods'][k][pos]
            if g != '나':
                counts[g] += 1
    total_chars = sum(ohaeng.values())
    god_groups = []
    me_elem = ELEMENT_ORDER.index(pillars['day']['gan_element'])
    for offset, (gname, members, desc) in enumerate(GOD_GROUPS):
        n = sum(counts[m] for m in members)
        # 비겁=같은 오행, 식상=내가 낳는 오행 … 순서가 오행 상생 순서와 같다
        elem = ELEMENT_ORDER[(me_elem + offset) % 5]
        god_groups.append({'name': gname, 'desc': desc, 'count': n, 'element': elem, 'element_ko': ELEMENT_KO[elem],
                           'members': [(m, counts[m]) for m in members],
                           'pct': round(n / (total_chars - 1) * 100) if total_chars > 1 else 0})
    support = sum(g['count'] for g in god_groups if g['name'] in ('비겁', '인성')) + 1  # 일간 자신 포함
    strength = {
        'support': support, 'drain': total_chars - support,
        'label': '일간을 돕는 기운이 많은 편 (신강 경향)' if support > total_chars / 2
        else '일간을 빼는 기운이 많은 편 (신약 경향)' if support < total_chars / 2
        else '돕는 기운과 빼는 기운이 비슷함 (중화 경향)',
    }

    elements = [{'key': e, 'ko': ELEMENT_KO[e], 'count': ohaeng[e],
                 'pct': interp['ohaeng_analysis']['percentages'][e]} for e in ELEMENT_ORDER]

    # 대운·세운
    current = interp['current_daewoon']
    daewoon = interp['daewoon']
    current_idx = daewoon.index(current) if current else -1
    nxt = daewoon[current_idx + 1] if 0 <= current_idx < len(daewoon) - 1 else (daewoon[0] if current is None and daewoon else None)
    seun = []
    for dw in daewoon:
        years = []
        for y in range(dw['start_year'], dw['end_year'] + 1):
            yp = saju.year_pillar_of(y)
            years.append({'year': y, 'age': y - b.year, 'gan': yp['gan'], 'zhi': yp['zhi'],
                          'gan_element': yp['gan_element'], 'zhi_element': yp['zhi_element'],
                          'gan_god': saju.ten_god_of(day_gan, gan_idx=yp['gan_idx']),
                          'zhi_god': saju.ten_god_of(day_gan, zhi_idx=yp['zhi_idx']),
                          'current': y == today.year})
        seun.append(years)
    # 올해 세운은 입춘 기준 (1월 1일~입춘 전에는 아직 지난해 간지)
    now = datetime.datetime.now(KST).replace(tzinfo=None)
    this_year = saju.get_gan_zhi(now.year, now.month, now.day, now.hour, now.minute, solar_time=False)['year']
    this_year_info = {'year': today.year, 'pillar': this_year,
                      'gan_god': saju.ten_god_of(day_gan, gan_idx=this_year['gan_idx']),
                      'zhi_god': saju.ten_god_of(day_gan, zhi_idx=this_year['zhi_idx'])}

    # 계산 기준 (신뢰 표기)
    t = saju.resolve_time(b, inp['solar_time'], inp['region'])
    off = t['utc_offset']
    off_txt = f"UTC+{off.seconds // 3600}" + (f":{(off.seconds % 3600) // 60:02d}" if off.seconds % 3600 else "")
    basis = {
        'utc': off_txt + (" (서머타임)" if t['dst'] else ""),
        'dst_note': None if inp['time_unknown'] else {
            'gap': '서머타임 시작으로 시계에 없던 시각입니다. 표준시로 보고 계산했습니다.',
            'fold': '서머타임이 끝나며 두 번 있었던 시각입니다. 앞의(서머타임) 시각으로 계산했습니다.',
        }.get(t['dst_note']),
        'clock': None if inp['time_unknown'] else t['clock'].strftime('%H:%M'),
        'region': REGIONS[inp['region']][0],
        'longitude': t['longitude'],
        'solar_time': inp['solar_time'],
        'zishi': '야자시(23시대는 당일 일주)' if inp['zishi'] == 'split' else '23시부터 다음날 일주',
        'direction': '순행' if (daewoon and daewoon[0]['forward']) else '역행',
        'start_age': daewoon[0]['age'] if daewoon else None,
        'start_date': daewoon[0]['start_date'] if daewoon else None,
    }
    if inp['calendar'] == 'lunar':
        y, m, d = inp['input_ymd']
        basis['lunar'] = f"음력 {y}년 {'윤' if inp['leap'] else ''}{m}월 {d}일"

    age = full_age(b.date(), today)
    ten_stars_list = ", ".join(f"{k} {v}" for k, v in counts.most_common())
    ai_pillars = dict(pillars)
    if inp['time_unknown']:
        ai_pillars['hour'] = {'gan': '?', 'zhi': '?'}
    ctx = ai.build_context(
        inp['name'], inp['gender'], ai_pillars, interp['ohaeng_analysis'], ten_stars_list,
        _dw_label(current), _dw_label(nxt) if nxt else "없음", f"{b.year}년생 (만 {age}세)",
        f"{today.year}년 {today.month}월 {today.day}일",
    )
    return {
        'pillars': pillars,
        'table': table,
        'ohaeng': ohaeng,
        'elements': elements,
        'god_groups': god_groups,
        'strength': strength,
        'interp': interp,
        'daewoon': daewoon,
        'current_idx': current_idx,
        'seun': seun,
        'this_year': this_year_info,
        'basis': basis,
        'age': age,
        'zodiac': saju.zodiac(pillars),
        'ai_ctx': ctx,
    }


# ----------------------------------------------------------------------
# 사용량 제한 (공개 배포용) — 외부 방문자만 센다
# ----------------------------------------------------------------------
LIMIT_PER_IP = int(os.getenv("RATE_LIMIT_PER_IP", "5"))
LIMIT_TOTAL = int(os.getenv("RATE_LIMIT_TOTAL", "200"))
MAX_ATTEMPTS = 3          # 분석 ID 하나로 묶음마다 시도할 수 있는 횟수 (실패 재시도 포함)
TRUST_LOCAL = os.getenv("TRUST_LOCAL_UNLIMITED", "1") == "1"  # 운영(plist)에서는 0


class Quota:
    def __init__(self):
        self._lock = threading.Lock()
        self._day = None
        self._ip = Counter()
        self._total = 0

    def take(self, ip):
        """한 번 차감. 한도를 넘으면 False"""
        today = datetime.datetime.now(KST).date()
        with self._lock:
            if self._day != today:
                self._day, self._ip, self._total = today, Counter(), 0
            if self._ip[ip] >= LIMIT_PER_IP or self._total >= LIMIT_TOTAL:
                return False
            self._ip[ip] += 1
            self._total += 1
            return True


quota = Quota()


class AnalysisStore:
    """결과 화면을 연 사람만 AI 해석을 받아가도록 분석 ID → 계산 맥락을 잠시 보관"""

    def __init__(self, max_items=2000, ttl=3600):
        self._lock = threading.Lock()
        self._items = OrderedDict()
        self.max_items, self.ttl = max_items, ttl

    def put(self, ctx):
        aid = secrets.token_urlsafe(16)
        now = datetime.datetime.now().timestamp()
        with self._lock:
            self._items[aid] = (now, ctx, Counter())
            while len(self._items) > self.max_items:
                self._items.popitem(last=False)
        return aid

    def get(self, aid):
        with self._lock:
            item = self._items.get(aid)
        if not item or datetime.datetime.now().timestamp() - item[0] > self.ttl:
            return None
        return item[1]

    def attempt(self, aid, group):
        """묶음별 시도 횟수를 하나 올리고, 허용 범위면 True"""
        with self._lock:
            item = self._items.get(aid)
            if not item:
                return False
            item[2][group] += 1
            return item[2][group] <= MAX_ATTEMPTS

    def refund(self, aid, group):
        """claude를 실행하지 못하고 돌려보낸 시도(대기 초과)는 횟수에서 뺀다"""
        with self._lock:
            item = self._items.get(aid)
            if item and item[2][group] > 0:
                item[2][group] -= 1


store = AnalysisStore()


def client_ip():
    """Cloudflare 터널 뒤면 CF-Connecting-IP, 아니면 접속 주소. 로컬 직접 접속은 None(무제한)"""
    cf = request.headers.get('CF-Connecting-IP')
    addr = (cf or request.remote_addr or '').strip()
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return addr or 'unknown'
    if not cf and ip.is_loopback and TRUST_LOCAL:
        return None
    if ip.version == 6:
        # IPv6는 한 사람이 /64 대역 안에서 주소를 쉽게 바꿀 수 있어 대역 단위로 센다
        return str(ipaddress.ip_network(f"{ip}/64", strict=False))
    return str(ip)


# ----------------------------------------------------------------------
# 라우트
# ----------------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html', form={}, error=None, error_field=None)


@app.route('/loading', methods=['POST'])
def legacy_loading():
    # 예전 로딩 화면 경로 호환
    return result()


@app.route('/result', methods=['POST'])
def result():
    try:
        inp = parse_input(request.form)
    except InputError as e:
        return render_template('index.html', form=request.form, error=str(e), error_field=e.field), 400

    data = analyze(inp)
    ai_state, analysis_id = 'off', None
    if ai.available:
        ip = client_ip()
        if ip is None or ai.is_cached(data['ai_ctx']) or quota.take(ip):
            ai_state, analysis_id = 'on', store.put(data['ai_ctx'])
        else:
            ai_state = 'limited'

    b = inp['birth']
    return render_template(
        'result.html',
        inp=inp,
        birth_date=b.strftime('%Y-%m-%d'),
        birth_time=None if inp['time_unknown'] else b.strftime('%H:%M'),
        ai_groups=list(GROUPS),
        ai_state=ai_state,
        analysis_id=analysis_id,
        limits={'ip': LIMIT_PER_IP, 'total': LIMIT_TOTAL},
        **data,
    )


@app.route('/api/analysis/<analysis_id>/<group>', methods=['POST'])
def api_analysis(analysis_id, group):
    if group not in GROUPS:
        return jsonify(error="알 수 없는 분석 항목입니다."), 404
    ctx = store.get(analysis_id)
    if ctx is None:
        return jsonify(error="분석 시간이 지났습니다. 처음 화면에서 다시 조회해 주세요."), 410
    if not store.attempt(analysis_id, group):
        return jsonify(error="이 풀이는 여러 번 실패해 더 시도할 수 없습니다. 처음 화면에서 다시 조회해 주세요."), 429
    try:
        res = ai.get_group(group, ctx)
    except Busy:
        store.refund(analysis_id, group)
        return jsonify(error="지금 풀이를 요청한 분이 많습니다. 잠시 후 다시 불러와 주세요.", retry=True), 503
    if not res:
        return jsonify(error="AI 풀이를 만들지 못했습니다. 다시 불러오기를 눌러 주세요.", retry=True), 502
    return jsonify(group=group, data=res)


def _git_sha():
    try:
        return subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, timeout=5,
                              cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip() or None
    except Exception:
        return None


GIT_SHA = _git_sha()  # 배포 검증용 — 디스크가 아니라 실행 중인 프로세스의 커밋


@app.after_request
def security_headers(resp):
    resp.headers.setdefault('X-Frame-Options', 'DENY')
    resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
    resp.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    resp.headers.setdefault('Content-Security-Policy', (
        # Cloudflare 방문 통계(beacon)는 프록시가 자동으로 넣으므로 허용
        "default-src 'self'; script-src 'self' 'unsafe-inline' https://static.cloudflareinsights.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        "font-src 'self' data: https://cdn.jsdelivr.net https://fonts.gstatic.com; "
        "img-src 'self' data:; connect-src 'self' https://cloudflareinsights.com; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    ))
    return resp


@app.route('/healthz')
def healthz():
    return jsonify(ok=True, ai=ai.available, sha=GIT_SHA)


if __name__ == '__main__':
    app.run(host=os.getenv('HOST', '127.0.0.1'),
            port=int(os.getenv('PORT', '5050')),
            debug=os.getenv('FLASK_DEBUG') == '1',
            threaded=True)
