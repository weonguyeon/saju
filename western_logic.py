"""서양 점성술 출생차트 (Natal chart)

행성 위치는 astronomy-engine(MIT), ASC·MC·하우스·애스펙트는 아래 공식으로 직접 계산한다.
Swiss Ephemeris(AGPL) 계산값과 각초 단위로 일치하는지 tests/test_western.py 에서 대조한다.
"""
import math

import astronomy as ae

SIGNS = [
    ('양자리', '♈'), ('황소자리', '♉'), ('쌍둥이자리', '♊'), ('게자리', '♋'),
    ('사자자리', '♌'), ('처녀자리', '♍'), ('천칭자리', '♎'), ('전갈자리', '♏'),
    ('사수자리', '♐'), ('염소자리', '♑'), ('물병자리', '♒'), ('물고기자리', '♓'),
]
SIGN_ELEMENT = ['불', '흙', '공기', '물'] * 3  # 양=불, 황소=흙, 쌍둥이=공기, 게=물 …

PLANETS = [
    ('sun', '태양', '☉', ae.Body.Sun),
    ('moon', '달', '☽', ae.Body.Moon),
    ('mercury', '수성', '☿', ae.Body.Mercury),
    ('venus', '금성', '♀', ae.Body.Venus),
    ('mars', '화성', '♂', ae.Body.Mars),
    ('jupiter', '목성', '♃', ae.Body.Jupiter),
    ('saturn', '토성', '♄', ae.Body.Saturn),
    ('uranus', '천왕성', '♅', ae.Body.Uranus),
    ('neptune', '해왕성', '♆', ae.Body.Neptune),
    ('pluto', '명왕성', '♇', ae.Body.Pluto),
]

# (각도, 이름, 허용 오차)
ASPECTS = [
    (0, '합', 8),
    (60, '섹스타일', 6),
    (90, '스퀘어', 7),
    (120, '트라인', 8),
    (180, '대립', 8),
]

R, D = math.radians, math.degrees


def _norm(x):
    return x % 360.0


def _diff(a, b):
    """a - b 를 -180~180 으로"""
    return (a - b + 180.0) % 360.0 - 180.0


def sign_of(lon):
    lon = _norm(lon)
    i = int(lon // 30)
    return {'index': i, 'name': SIGNS[i][0], 'symbol': SIGNS[i][1], 'element': SIGN_ELEMENT[i],
            'degree': lon - i * 30}


def _ecliptic_lon(body, t):
    if body == ae.Body.Sun:
        return ae.SunPosition(t).elon
    if body == ae.Body.Moon:
        return ae.EclipticGeoMoon(t).lon
    return ae.Ecliptic(ae.GeoVector(body, t, True)).elon


def _obliquity(t):
    # 평균 황도경사 (IAU 간이식). 하우스 계산 오차는 각초 단위로 충분히 작다
    T = t.tt / 36525.0
    return 23.4392911 - 0.0130041667 * T


def angles(ramc, eps, lat):
    mc = D(math.atan2(math.sin(R(ramc)), math.cos(R(ramc)) * math.cos(R(eps))))
    asc = D(math.atan2(math.cos(R(ramc)),
                       -(math.sin(R(ramc)) * math.cos(R(eps)) + math.tan(R(lat)) * math.sin(R(eps)))))
    return _norm(asc), _norm(mc)


def placidus(ramc, eps, lat):
    """Placidus 하우스 커스프 12개 (반호 반복법). 극지방(|위도| > 66°)에서는 정의되지 않아 None"""
    if abs(lat) > 66.0:
        return None

    def cusp(base, k):
        ra = ramc + base + k * 90
        lam = 0.0
        for _ in range(60):
            lam = D(math.atan2(math.sin(R(ra)), math.cos(R(ra)) * math.cos(R(eps))))
            dec = D(math.asin(math.sin(R(eps)) * math.sin(R(lam))))
            x = math.tan(R(lat)) * math.tan(R(dec))
            if abs(x) > 1:
                return None
            dsa = 90 + D(math.asin(x))
            ra = ramc + base + k * dsa
        return _norm(lam)

    asc, mc = angles(ramc, eps, lat)
    c = {1: asc, 10: mc, 11: cusp(0, 1 / 3), 12: cusp(0, 2 / 3), 2: cusp(60, 2 / 3), 3: cusp(120, 1 / 3)}
    if any(v is None for v in c.values()):
        return None
    for h in (1, 2, 3, 10, 11, 12):
        c[(h + 6 - 1) % 12 + 1] = _norm(c[h] + 180)
    return [c[i] for i in range(1, 13)]


def whole_sign(asc):
    start = int(_norm(asc) // 30) * 30
    return [_norm(start + 30 * i) for i in range(12)]


def house_of(lon, cusps):
    lon = _norm(lon)
    for i in range(12):
        a, b = cusps[i], cusps[(i + 1) % 12]
        span = _norm(b - a)
        if _norm(lon - a) < span:
            return i + 1
    return 12


def natal_chart(utc, lat, lon):
    """utc: naive UTC datetime, lat/lon: 도 단위(동경 +)"""
    t = ae.Time.Make(utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second + utc.microsecond / 1e6)
    eps = _obliquity(t)
    ramc = _norm(ae.SiderealTime(t) * 15 + lon)
    asc, mc = angles(ramc, eps, lat)
    cusps = placidus(ramc, eps, lat)
    house_system = 'Placidus'
    if cusps is None:
        cusps, house_system = whole_sign(asc), 'Whole Sign'

    planets = []
    for key, name, symbol, body in PLANETS:
        lon_ = _norm(_ecliptic_lon(body, t))
        # 하루 뒤 위치와 비교해 역행 여부 (해·달은 역행 없음)
        retro = False
        if key not in ('sun', 'moon'):
            retro = _diff(_ecliptic_lon(body, t.AddDays(1)), lon_) < 0
        planets.append({'key': key, 'name': name, 'symbol': symbol, 'lon': lon_, 'sign': sign_of(lon_),
                        'house': house_of(lon_, cusps), 'retro': retro})

    aspects = []
    for i in range(len(planets)):
        for j in range(i + 1, len(planets)):
            sep = abs(_diff(planets[i]['lon'], planets[j]['lon']))
            for angle, aname, orb in ASPECTS:
                if abs(sep - angle) <= orb:
                    aspects.append({'a': planets[i], 'b': planets[j], 'name': aname, 'angle': angle,
                                    'orb': round(sep - angle, 1)})
    aspects.sort(key=lambda x: abs(x['orb']))

    elements = {'불': 0, '흙': 0, '공기': 0, '물': 0}
    for p in planets:
        elements[p['sign']['element']] += 1

    return {
        'asc': {'lon': asc, 'sign': sign_of(asc)},
        'mc': {'lon': mc, 'sign': sign_of(mc)},
        'house_system': house_system,
        'cusps': [{'house': i + 1, 'lon': c, 'sign': sign_of(c)} for i, c in enumerate(cusps)],
        'planets': planets,
        'aspects': aspects,
        'elements': elements,
    }


def fmt_pos(lon):
    # 분 단위로 먼저 반올림해야 29°59.99′ 가 '30°00′' 이 아니라 다음 별자리 0°00′ 이 된다
    total = int(round(_norm(lon) * 60)) % (360 * 60)
    s = sign_of(total / 60)
    within = total - s['index'] * 30 * 60
    return f"{s['name']} {within // 60}°{within % 60:02d}′"


def _spread(lons, min_gap):
    """가까운 각도들을 최소 간격(min_gap도) 이상 벌린 표시 각도.

    원을 가장 큰 빈 구간에서 끊어 직선으로 편 뒤, 가까운 점들을 무리로 묶어 무리의 원래 중심을 기준으로
    min_gap 간격으로 고르게 펼친다. 펼친 무리가 이웃과 겹치면 합쳐 다시 펼치기를 반복한다(순서 보존).
    """
    n = len(lons)
    if n < 2:
        return list(lons)
    order = sorted(range(n), key=lambda k: _norm(lons[k]))
    xs = [_norm(lons[k]) for k in order]
    gaps = [_norm(xs[(i + 1) % n] - xs[i]) or (360.0 if n == 1 else 0.0) for i in range(n)]
    cut = max(range(n), key=lambda i: gaps[i])          # 가장 큰 빈 구간 뒤에서 시작
    start = (cut + 1) % n
    line, base = [], xs[start]
    for i in range(n):
        line.append(_norm(xs[(start + i) % n] - base))   # 0 부터 증가하는 직선 좌표

    clusters = [[i] for i in range(n)]

    def layout(cl):
        center = sum(line[i] for i in cl) / len(cl)
        return [center + (j - (len(cl) - 1) / 2) * min_gap for j in range(len(cl))]

    pos = {i: line[i] for i in range(n)}
    merged = True
    while merged:
        merged = False
        for ci in range(len(clusters) - 1):
            a, b = clusters[ci], clusters[ci + 1]
            if pos[b[0]] - pos[a[-1]] < min_gap - 1e-9:
                clusters[ci:ci + 2] = [a + b]
                for idx, p in zip(clusters[ci], layout(clusters[ci])):
                    pos[idx] = p
                merged = True
                break

    out = [0.0] * n
    for i in range(n):
        out[order[(start + i) % n]] = _norm(base + pos[i])
    return out


def wheel(chart, size=340):
    """원형 차트 SVG 좌표. 상승궁을 왼쪽(9시)에 두고 황경이 반시계 방향으로 커진다.
    시간을 모르면 양자리 0°를 왼쪽에 둔다. 행성 기호는 겹치지 않게 벌려 놓고, 실제 자리는 안쪽 눈금+연결선으로 표시"""
    c = size / 2
    ref = chart['asc']['lon'] if not chart.get('time_unknown') else 0.0
    r_out, r_sign = c - 4, c - 34
    r_planet = r_sign - 20          # 행성 기호
    r_tick = r_sign - 40            # 실제 자리 눈금 (안쪽 원 바로 바깥)
    r_in = r_sign - 46              # 안쪽 원 (하우스 번호 + 애스펙트)
    r_hnum = r_in - 11              # 하우스 번호
    r_asp = r_in - 22               # 애스펙트 선 끝

    def pt(lon, r):
        a = math.radians(180 + (lon - ref))
        return round(c + r * math.cos(a), 1), round(c - r * math.sin(a), 1)

    signs = []
    for i, (name, sym) in enumerate(SIGNS):
        x1, y1 = pt(i * 30, r_out)
        x2, y2 = pt(i * 30, r_sign)
        lx, ly = pt(i * 30 + 15, (r_out + r_sign) / 2)
        signs.append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'lx': lx, 'ly': ly, 'symbol': sym, 'name': name,
                      'element': ['fire', 'earth', 'metal', 'water'][i % 4]})

    # 기호 사이 최소 간격: 원주에서 약 22px (연결선이 몰리지 않게)
    min_gap = math.degrees(22 / r_planet)
    disp = _spread([p['lon'] for p in chart['planets']], min_gap)
    placed = []
    for p, d in zip(chart['planets'], disp):
        x, y = pt(d, r_planet)
        lx1, ly1 = pt(d, r_planet - 9)
        tx, ty = pt(p['lon'], r_tick)
        k1x, k1y = pt(p['lon'], r_in)
        placed.append({'x': x, 'y': y, 'lx': lx1, 'ly': ly1, 'tx': tx, 'ty': ty, 'kx': k1x, 'ky': k1y,
                       'symbol': p['symbol'], 'name': p['name'], 'key': p['key'], 'retro': p['retro']})

    lines = []
    for a in chart['aspects']:
        if a['name'] == '합':
            continue
        x1, y1 = pt(a['a']['lon'], r_asp)
        x2, y2 = pt(a['b']['lon'], r_asp)
        lines.append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                      'kind': 'hard' if a['name'] in ('스퀘어', '대립') else 'soft'})

    houses = []
    if not chart.get('time_unknown'):
        cusps = [cu['lon'] for cu in chart['cusps']]
        for i, cu in enumerate(chart['cusps']):
            x1, y1 = pt(cu['lon'], r_sign)
            x2, y2 = pt(cu['lon'], r_asp)
            mid = cu['lon'] + _norm(cusps[(i + 1) % 12] - cu['lon']) / 2   # 하우스 가운데에 번호
            hx, hy = pt(mid, r_hnum)
            houses.append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'n': cu['house'], 'hx': hx, 'hy': hy,
                           'angle': cu['house'] in (1, 4, 7, 10)})
    return {'size': size, 'c': c, 'r_out': r_out, 'r_sign': r_sign, 'r_in': r_in, 'r_asp': r_asp,
            'signs': signs, 'planets': placed, 'lines': lines, 'houses': houses}
