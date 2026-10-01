import datetime

import pytest

from saju_logic import SajuLogic, TWELVE_STAGES as s_STAGES

s = SajuLogic()


def gz(y, mo, d, h, mi, **kw):
    p = s.get_gan_zhi(y, mo, d, h, mi, **kw)
    return [p[k]['gan'] + p[k]['zhi'] for k in ('year', 'month', 'day', 'hour')]


def test_known_day_pillar_2000_01_01():
    # 2000-01-01 = 무오일 (만세력 기준점으로 널리 쓰이는 값)
    assert gz(2000, 1, 1, 12, 0, solar_time=False)[2] == '무오'


@pytest.mark.parametrize("h,mi,year", [(17, 20, '계묘'), (17, 35, '갑진')])
def test_year_changes_at_ipchun_kst(h, mi, year):
    # 2024 입춘 = 2월 4일 17:27 (한국 시각)
    assert gz(2024, 2, 4, h, mi, solar_time=False)[0] == year


@pytest.mark.parametrize("h,mi,month", [(11, 10, '병인'), (11, 35, '정묘')])
def test_month_changes_at_gyeongchip_kst(h, mi, month):
    # 2024 경칩 = 3월 5일 11:22 (한국 시각) → 인월에서 묘월로
    assert gz(2024, 3, 5, h, mi, solar_time=False)[1] == month


def test_old_bug_feb4_before_ipchun():
    # 예전 코드는 2월 4일이면 무조건 새해로 넘겼다 — 1990 입춘은 2/4 11:14(KST)
    assert gz(1990, 2, 4, 10, 0, solar_time=False)[0] == '기사'
    assert gz(1990, 2, 4, 12, 0, solar_time=False)[0] == '경오'


def test_old_bug_month_cut_on_5th():
    # 예전 코드는 매달 5일에 월을 바꿨다 — 1990 경칩은 3/6 05:19(KST)라 3/5는 아직 인월(무인)
    assert gz(1990, 3, 5, 12, 0, solar_time=False)[1] == '무인'
    assert gz(1990, 3, 6, 12, 0, solar_time=False)[1] == '기묘'


def test_zishi_options():
    split = gz(1995, 8, 8, 23, 30, solar_time=False, zishi='split')
    nxt = gz(1995, 8, 8, 23, 30, solar_time=False, zishi='next')
    assert split[2] == '신미' and nxt[2] == '임신'   # 일주: 당일 vs 다음날
    assert split[3] == nxt[3] == '경자'              # 시주는 둘 다 다음날 자시


def test_solar_time_correction_moves_hour_boundary():
    # 13:25 는 표준시로는 미시, 서울 경도 보정(-32분)하면 오시
    assert gz(1990, 5, 15, 13, 25, solar_time=False)[3][1] == '미'
    assert gz(1990, 5, 15, 13, 10, solar_time=True)[3][1] == '오'


def test_ten_gods():
    p = s.get_gan_zhi(1990, 5, 15, 14, 30, solar_time=False)  # 경오 신사 경진 계미, 일간 경금
    tg = s._get_all_sip_seong(p)
    assert tg['day']['gan'] == '나'
    assert tg['year']['gan'] == '비견'   # 경
    assert tg['month']['gan'] == '겁재'  # 신
    assert tg['hour']['gan'] == '상관'   # 계
    assert tg['year']['zhi'] == '정관'   # 오(정화)
    assert tg['month']['zhi'] == '편관'  # 사(병화)


def _dw(gender, birth=datetime.datetime(1990, 5, 15, 14, 30)):
    p = s.get_gan_zhi(birth.year, birth.month, birth.day, birth.hour, birth.minute)
    return s.calculate_daewoon_list(birth, gender, p['day']['gan_idx'])


def test_daewoon_direction_and_spacing():
    male, female = _dw('male'), _dw('female')  # 경오년 = 양년
    assert male[0]['forward'] is True and female[0]['forward'] is False
    assert [d['gan'] + d['zhi'] for d in male[:2]] == ['임오', '계미']    # 월주 신사에서 순행
    assert [d['gan'] + d['zhi'] for d in female[:2]] == ['경진', '기묘']  # 역행
    for lst in (male, female):
        assert 0 <= lst[0]['age'] <= 10
        for a, b in zip(lst, lst[1:]):
            assert b['age'] - a['age'] == 10
            assert b['start_year'] - a['start_year'] == 10


def test_daewoon_start_not_fixed_any_more():
    # 예전 코드는 누구나 4세 시작이었다
    ages = {_dw('male', datetime.datetime(1990, m, 15, 12, 0))[0]['age'] for m in range(1, 13)}
    assert len(ages) > 1


def test_current_daewoon():
    lst = _dw('male')
    assert s.current_daewoon(lst, datetime.date(1990, 6, 1)) is None
    cur = s.current_daewoon(lst, datetime.date(2026, 10, 1))
    assert cur['start_year'] <= 2026 <= cur['end_year']


def test_balance_text_reflects_distribution():
    assert '없어' in s._get_balance_text({'wood': 0, 'fire': 2, 'earth': 2, 'metal': 3, 'water': 1})
    assert '골고루' in s._get_balance_text({'wood': 2, 'fire': 2, 'earth': 1, 'metal': 2, 'water': 1})


def test_today_fortune_uses_given_date():
    t = s.get_today_fortune(6, 'male', datetime.date(2000, 1, 1))
    assert t['pillar'] == '무오일' and t['date'] == '2000년 1월 1일'


def test_dst_1988_is_removed_by_solar_time():
    # 1988-07-01 은 서머타임(UTC+10). 시계 13:20 = 표준시 12:20 → 서울 태양시 11:48 = 오시
    assert gz(1988, 7, 1, 13, 20, solar_time=True)[3][1] == '오'
    assert gz(1988, 7, 1, 13, 20, solar_time=False)[3][1] == '미'


def test_utc_0830_era():
    # 1958년 표준시는 UTC+8:30 → 같은 시계 시각이라도 태양시가 30분 늦지 않다 (12:10 시계 = 서울 12:08)
    assert gz(1958, 1, 1, 12, 10, solar_time=True)[3][1] == '오'


def test_regions_shift_boundary():
    # 13:28 부산(경도 129.08 → -24분) = 13:04 미시, 서울(-32분) = 12:56 오시
    assert gz(1990, 5, 15, 13, 28, region='busan')[3][1] == '미'
    assert gz(1990, 5, 15, 13, 28, region='seoul')[3][1] == '오'


def test_lunar_input():
    assert s.lunar_to_solar(2020, 4, 15, leap=True) == datetime.date(2020, 6, 6)
    with pytest.raises(ValueError):
        s.lunar_to_solar(2021, 4, 1, leap=True)   # 2021년엔 윤4월 없음
    with pytest.raises(ValueError):
        s.lunar_to_solar(2021, 1, 30)             # 2021 음력 1월은 29일까지


def test_twelve_stages_match_library_and_hidden_stems():
    from lunar_python import Solar
    import random
    random.seed(3)
    for _ in range(200):
        d = datetime.date(1950, 1, 1) + datetime.timedelta(days=random.randrange(0, 365 * 70))
        ec = Solar.fromYmdHms(d.year, d.month, d.day, 12, 0, 0).getLunar().getEightChar()
        p = s._to_pillar(ec.getDay())
        for zhi_h, stage_h in [(ec.getYearZhi(), ec.getYearDiShi()), (ec.getDayZhi(), ec.getDayDiShi())]:
            zi = "子丑寅卯辰巳午未申酉戌亥".index(zhi_h)
            ko = dict(zip(['长生', '沐浴', '冠带', '临官', '帝旺', '衰', '病', '死', '墓', '绝', '胎', '养'], s_STAGES))[stage_h]
            assert s.twelve_stage(p['gan_idx'], zi) == ko
    assert s.hidden_stems(2) == ['무', '병', '갑']   # 인: 여기 무, 중기 병, 정기 갑
    assert s.hidden_stems(0) == ['임', '계']
    # 정기(마지막)는 그 지지의 본 오행과 같아야 한다
    for zi in range(12):
        assert s.STEM_OHAENG[s.CHEONGAN.index(s.hidden_stems(zi)[-1])] == s.BRANCH_OHAENG[zi]


def test_year_pillar_of():
    assert s.year_pillar_of(2024)['gan'] + s.year_pillar_of(2024)['zhi'] == '갑진'
    assert s.year_pillar_of(1984)['gan'] + s.year_pillar_of(1984)['zhi'] == '갑자'
