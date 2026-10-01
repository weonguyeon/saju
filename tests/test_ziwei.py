import datetime

from ziwei_logic import build_chart, time_index


def test_time_index_boundaries():
    d = datetime.datetime
    assert time_index(d(1990, 5, 15, 0, 10)) == (datetime.date(1990, 5, 15), 0)
    assert time_index(d(1990, 5, 15, 1, 0)) == (datetime.date(1990, 5, 15), 1)
    assert time_index(d(1990, 5, 15, 13, 58)) == (datetime.date(1990, 5, 15), 7)   # 미시
    assert time_index(d(1990, 5, 15, 22, 59)) == (datetime.date(1990, 5, 15), 11)
    assert time_index(d(1990, 5, 15, 23, 30), 'split') == (datetime.date(1990, 5, 16), 0)
    assert time_index(d(1990, 5, 15, 23, 30), 'next') == (datetime.date(1990, 5, 16), 0)


def test_chart_matches_hand_calculation():
    # 1990-05-15 미시 남자 — 안성결 손계산: 명궁 술(병술), 토오국, 자미 술·천부 오, 경년 사화
    c = build_chart(datetime.datetime(1990, 5, 15, 13, 58), 'male')
    assert c['soul_palace']['branch'] == 10 and c['soul_palace']['ganzhi'] == '병술'
    assert c['five_elements'] == '토오국'
    stars = {p['branch']: [s['name'] for s in p['major']] for p in c['palaces']}
    assert '자미' in stars[10] and '천부' in stars[6]
    mut = {m['star']: m['mutagen'] for m in c['mutagens']}
    assert mut['태양'] == '화록' and mut['무곡'] == '화권' and mut['태음'] == '화과' and mut['천동'] == '화기'
    assert c['soul_star'] == '녹존' and c['body_star'] == '화성'


def test_grid_layout():
    c = build_chart(datetime.datetime(1990, 5, 15, 13, 58), 'male')
    g = c['grid']
    assert [p['branch'] for p in g[0]] == [5, 6, 7, 8]
    assert [p['branch'] for p in g[3]] == [2, 1, 0, 11]
    assert g[1][1] is None and g[2][2] is None
    names = [p['name'] for p in c['palaces']]
    assert len(set(names)) == 12 and '명궁' in names
    assert sum(p['is_soul'] for p in c['palaces']) == 1 and sum(p['is_body'] for p in c['palaces']) == 1
    major_total = sum(len(p['major']) for p in c['palaces'])
    assert major_total == 14   # 주성 14개


def test_gender_changes_decadal_direction():
    m = build_chart(datetime.datetime(1990, 5, 15, 13, 58), 'male')
    f = build_chart(datetime.datetime(1990, 5, 15, 13, 58), 'female')
    assert m['soul_palace']['decadal'] == f['soul_palace']['decadal']   # 명궁 대한은 같다 (국수 시작)
    nxt = lambda c: [p for p in c['palaces'] if p['decadal'][0] == c['soul_palace']['decadal'][1] + 1][0]['branch']
    assert nxt(m) != nxt(f)   # 양남·음녀 순행 / 음남·양녀 역행


def test_month_end_late_zi_is_next_day():
    # 2023-02-19 23:26(보정 시각)은 음력 정월 29일 그믐 — 다음날(2월 초하루) 이른 자시 명반과 같아야 한다
    late = build_chart(datetime.datetime(2023, 2, 19, 23, 26), 'male')
    nxt = build_chart(datetime.datetime(2023, 2, 20, 0, 10), 'male')
    assert late['soul_palace']['ganzhi'] == nxt['soul_palace']['ganzhi'] == '을묘'
    assert late['five_elements'] == nxt['five_elements']
