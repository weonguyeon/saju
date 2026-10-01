import datetime

from lunar_python import Solar

from almanac_logic import day_info, good_days, birth_stars, YIJI_KO


def test_known_day_2026_10_01():
    d = day_info(datetime.date(2026, 10, 1), user_branch=2)   # 무신일 — 일지 신(申)과 충하는 인(호랑이)띠
    assert d['zhi_xing'] == '폐' and d['tian_shen'] == '백호' and not d['hwangdo']
    assert d['xiu'] == '규' and d['xiu_luck'] == '흉'
    assert d['chong'] == '호랑이' and d['clash_user'] is True
    assert d['lunar'] == '8.21' and d['weekday'] == '목'


def test_son_eomneun_rule():
    # 손없는날 = 음력 9·10·19·20·29·30일 (한국민족문화대백과 「손」)
    d = datetime.date(2026, 1, 1)
    for i in range(400):
        day = d + datetime.timedelta(days=i)
        lunar_day = Solar.fromYmd(day.year, day.month, day.day).getLunar().getDay()
        assert day_info(day)['son_eomneun'] == (lunar_day in (9, 10, 19, 20, 29, 30))


def test_all_terms_translated():
    d = datetime.date(2019, 1, 1)
    missing = set()
    for i in range(365 * 17):   # 2019~2035
        info = day_info(d + datetime.timedelta(days=i))
        missing |= {t for t in info['yi_raw'] + info['ji_raw'] if t not in YIJI_KO}
    assert not missing, missing


def test_good_days_rules():
    infos, picks = good_days(datetime.date(2026, 10, 1), days=60, user_branch=6)
    assert len(infos) == 60
    for key, p in picks.items():
        for d in p['days']:
            assert d['hwangdo'] and not d['clash_user']
    assert any(p['days'] for p in picks.values())


def test_birth_stars():
    # 1990-05-15 14:30 KST → 본명성 일백수성, 월명성 오황토성 (입춘 기준)
    s = birth_stars(datetime.datetime(1990, 5, 15, 13, 30))
    assert s['year']['name'] == '일백수성' and s['month']['name'] == '오황토성'
    # 입춘 전(1990-02-03)은 전년도(1989) 본명성 — 이흑토성
    assert birth_stars(datetime.datetime(1990, 2, 3, 12, 0))['year']['name'] == '이흑토성'
    # 입춘 당일 절입 시각 전후 (2000 입춘 = 북경시 2/4 20:40) — 사주 연주(기묘→경진)와 같은 경계
    assert birth_stars(datetime.datetime(2000, 2, 4, 20, 30))['year']['name'] == '일백수성'
    assert birth_stars(datetime.datetime(2000, 2, 4, 20, 50))['year']['name'] == '구자화성'
    # 경칩(북경시 3/5 14:42) 전은 아직 인월
    assert birth_stars(datetime.datetime(2000, 3, 5, 8, 0))['month']['name'] == '오황토성'
