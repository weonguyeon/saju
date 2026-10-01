"""자미두수(紫微斗數) 명반 — iztro-py(MIT, iztro 파이썬 포팅) 감싸기

시진은 사주 시주와 같은 보정 시각(경도·서머타임 보정한 태양시)으로 정해 두 체계가 서로 맞게 한다.
iztro-py 를 다른 구현(예: node 의 iztro)으로 바꿀 때는 build_chart 의 반환 모양만 지키면 된다.
"""
import datetime

from iztro_py import astro

KO = 'ko-KR'

# 명주·신주는 iztro-py 가 번역하지 않는 키로 준다 (예: lucunMin)
STAR_KO = {
    'tanlang': '탐랑', 'jumen': '거문', 'lucun': '녹존', 'wenqu': '문곡', 'lianzhen': '염정',
    'wuqu': '무곡', 'pojun': '파군', 'huoxing': '화성', 'tianxiang': '천상', 'tianliang': '천량',
    'tiantong': '천동', 'wenchang': '문창', 'tianji': '천기',
}
MUTAGEN_KO = {'禄': '화록', '权': '화권', '科': '화과', '忌': '화기',
              '祿': '화록', '權': '화권'}

# 명반 4×4 배치 (가운데 2×2 는 요약). 지지 순서 자축인묘…해 = 0~11
GRID = [
    [5, 6, 7, 8],      # 사 오 미 신
    [4, None, None, 9],    # 진       유
    [3, None, None, 10],   # 묘       술
    [2, 1, 0, 11],     # 인 축 자 해
]
BRANCH_KEYS = ['zi', 'chou', 'yin', 'mao', 'chen', 'si', 'wu', 'wei', 'shen', 'you', 'xu', 'hai']
BRANCH_KO = '자축인묘진사오미신유술해'


def time_index(clock, zishi='split'):
    """보정 시각 → (양력 날짜, iztro 시진 번호 0~12)

    0 = 이른 자시(00~01시), 1 = 축시 … 11 = 해시
    23시대는 자미두수 관례(晚子时按次日)대로 항상 다음날 이른 자시로 넘긴다.
    iztro-py 에 늦은 자시(12)를 주면 자미성은 다음날, 명궁은 그날로 계산해 그믐날 23시생 명반이 어긋난다.
    zishi 인자는 사주 쪽 옵션이라 여기서는 쓰지 않는다 (호출 모양 유지용)
    """
    h = clock.hour
    if h == 23:
        return clock.date() + datetime.timedelta(days=1), 0
    return clock.date(), (h + 1) // 2


def _star_key(raw):
    for suffix in ('Min', 'Maj'):
        if raw.endswith(suffix):
            raw = raw[:-len(suffix)]
    return raw


def _stars(stars):
    out = []
    for s in stars:
        out.append({
            'name': s.translate_name(KO),
            'brightness': s.translate_brightness(KO) if s.brightness else '',
            'mutagen': MUTAGEN_KO.get(s.mutagen or '', ''),
        })
    return out


def build_chart(clock, gender, zishi='split'):
    """clock: 보정된 출생 시각(naive), gender: 'male'/'female'"""
    date, idx = time_index(clock, zishi)
    c = astro.by_solar(f"{date.year}-{date.month}-{date.day}", idx, '男' if gender == 'male' else '女', language=KO)

    soul_branch = BRANCH_KEYS.index(c.earthly_branch_of_soul_palace.replace('Earthly', ''))
    body_branch = BRANCH_KEYS.index(c.earthly_branch_of_body_palace.replace('Earthly', ''))

    by_branch = {}
    for p in c.palaces:
        b = BRANCH_KEYS.index(p.earthly_branch.replace('Earthly', ''))
        major = _stars(p.major_stars)
        by_branch[b] = {
            'branch': b,
            'ganzhi': p.translate_heavenly_stem(KO) + p.translate_earthly_branch(KO),
            'name': p.translate_name(KO),
            'major': major,
            'minor': _stars(p.minor_stars),
            'adjective': [s.translate_name(KO) for s in p.adjective_stars],
            'decadal': list(p.decadal.range),
            'changsheng': p.changsheng12,
            'is_soul': b == soul_branch,
            'is_body': b == body_branch,
            'empty': not major,
        }

    mutagens = []
    for b, p in by_branch.items():
        for s in p['major'] + p['minor']:
            if s['mutagen']:
                mutagens.append({'star': s['name'], 'mutagen': s['mutagen'], 'palace': p['name']})
    order = ['화록', '화권', '화과', '화기']
    mutagens.sort(key=lambda m: order.index(m['mutagen']))

    grid = [[by_branch[b] if b is not None else None for b in row] for row in GRID]
    return {
        'grid': grid,
        'palaces': [by_branch[b] for b in range(12)],
        'soul_palace': by_branch[soul_branch],
        'body_palace': by_branch[body_branch],
        'five_elements': c.five_elements_class,
        'soul_star': STAR_KO.get(_star_key(c.soul), c.soul),
        'body_star': STAR_KO.get(_star_key(c.body), c.body),
        'lunar_date': c.lunar_date,
        'time_label': f"{c.time} ({c.time_range})",
        'mutagens': mutagens,
        'input_date': date,
        'time_index': idx,
    }
