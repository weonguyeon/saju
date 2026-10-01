import datetime

import pytest

from western_logic import natal_chart, sign_of, house_of, whole_sign, fmt_pos

# Swiss Ephemeris(Moshier) 계산값 — 앱에는 AGPL 라이브러리를 넣지 않고 기준 숫자만 둔다
REF = [
    {"ut": [1990, 5, 15, 5.5], "lat": 37.5665, "lon": 126.978,
     "planets": [54.135, 293.8241, 38.0478, 12.5095, 348.1327, 99.4905, 295.254, 279.1905, 284.3569, 226.175],
     "asc": 173.5996, "mc": 82.8067,
     "placidus": [173.5996, 199.6989, 229.8749, 262.8067, 295.8925, 326.571, 353.5996, 19.6989, 49.8749, 82.8067, 115.8925, 146.571]},
    {"ut": [1988, 7, 1, 3 + 20 / 60], "lat": 35.1796, "lon": 129.0756,
     "planets": [99.5108, 297.455, 79.6792, 74.1606, 353.6779, 56.0806, 268.4687, 268.6119, 278.7933, 219.8597],
     "asc": 187.074, "mc": 97.7861,
     "placidus": [187.074, 214.4895, 245.1344, 277.7861, 310.3474, 340.579, 7.074, 34.4895, 65.1344, 97.7861, 130.3474, 160.579]},
    {"ut": [2001, 12, 24, 14.75], "lat": 33.4996, "lon": 126.5312,
     "planets": [272.86, 22.0803, 283.9404, 267.8676, 341.4745, 101.6601, 69.8254, 322.1308, 307.1959, 255.7671],
     "asc": 172.3585, "mc": 81.7074,
     "placidus": [172.3585, 199.1226, 229.3907, 261.7074, 294.0675, 324.6799, 352.3585, 19.1226, 49.3907, 81.7074, 114.0675, 144.6799]},
]
TOL = 0.01  # 도 (36각초). 실측 오차는 수 각초


def _d(a, b):
    return abs((a - b + 180) % 360 - 180)


def _utc(ut):
    y, m, d, h = ut
    return datetime.datetime(y, m, d) + datetime.timedelta(hours=h)


@pytest.mark.parametrize("ref", REF)
def test_matches_swiss_ephemeris(ref):
    c = natal_chart(_utc(ref["ut"]), ref["lat"], ref["lon"])
    for p, want in zip(c["planets"], ref["planets"]):
        assert _d(p["lon"], want) < TOL, (p["key"], p["lon"], want)
    assert _d(c["asc"]["lon"], ref["asc"]) < TOL
    assert _d(c["mc"]["lon"], ref["mc"]) < TOL
    assert c["house_system"] == "Placidus"
    for cu, want in zip(c["cusps"], ref["placidus"]):
        assert _d(cu["lon"], want) < TOL


def test_signs_and_format():
    assert sign_of(0)["name"] == "양자리" and sign_of(359.9)["name"] == "물고기자리"
    assert sign_of(54.135)["name"] == "황소자리"
    assert fmt_pos(54.135) == "황소자리 24°08′"
    assert fmt_pos(29.9999) == "황소자리 0°00′" and fmt_pos(359.9999) == "양자리 0°00′"


def test_house_assignment_wraps():
    cusps = whole_sign(350)   # ASC 물고기 20° → 1하우스 = 물고기 0°(330°)부터
    assert house_of(345, cusps) == 1 and house_of(15, cusps) == 2 and house_of(325, cusps) == 12


def test_polar_falls_back_to_whole_sign():
    c = natal_chart(datetime.datetime(1990, 6, 21, 12), 70.0, 25.0)
    assert c["house_system"] == "Whole Sign"


def test_aspects_and_retrograde():
    c = natal_chart(_utc(REF[0]["ut"]), REF[0]["lat"], REF[0]["lon"])
    names = {(a["a"]["key"], a["b"]["key"], a["name"]) for a in c["aspects"]}
    assert ("sun", "moon", "트라인") in names          # 54.1° vs 293.8° → 120.3°
    assert all(abs(a["orb"]) <= 8 for a in c["aspects"])
    assert sum(c["elements"].values()) == 10
    assert not c["planets"][0]["retro"] and not c["planets"][1]["retro"]


@pytest.mark.parametrize("ref", REF)
def test_wheel_symbols_do_not_overlap(ref):
    import math
    from western_logic import wheel
    w = wheel(natal_chart(_utc(ref["ut"]), ref["lat"], ref["lon"]))
    ps = w["planets"]
    assert min(math.dist((a["x"], a["y"]), (b["x"], b["y"])) for i, a in enumerate(ps) for b in ps[i + 1:]) >= 18
    assert min(math.dist((h["hx"], h["hy"]), (p["x"], p["y"])) for h in w["houses"] for p in ps) >= 20


def test_spread_keeps_far_points_and_separates_cluster():
    from western_logic import _spread
    out = _spread([100, 101, 102, 250], 6)
    assert abs(out[3] - 250) < 1e-6
    gaps = sorted(out[:3])
    assert gaps[1] - gaps[0] >= 5.9 and gaps[2] - gaps[1] >= 5.9
    assert abs(sum(out[:3]) / 3 - 101) < 0.1   # 무리 중심은 그대로


def test_spread_identical_and_wraparound():
    from western_logic import _spread, _norm
    for pts in ([10] * 5, [0, 1, 359, 358, 180], [355, 356, 357, 2, 3]):
        out = sorted(_spread(pts, 6))
        gaps = [(_norm(out[(i + 1) % len(out)] - out[i])) for i in range(len(out))]
        assert min(gaps) >= 5.9, (pts, out)
