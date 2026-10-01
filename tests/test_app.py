import re

import pytest

import app as app_module
from app import app

FORM = dict(name='테스트', gender='male', calendar='solar', year='1990', month='5', day='15',
            birth_time='14:30', region='seoul', opts='1', solar_time='1', zishi='split')


@pytest.fixture
def client(monkeypatch):
    calls = []

    def fake_group(group, ctx):
        calls.append(group)
        if group == 'life':
            return {'gmhs': {'year': '초년 풀이', 'month': '청년 풀이', 'day': '중년 풀이', 'hour': '말년 풀이'}}
        keys = app_module.GROUPS[group]['keys']
        return {k: f'{k} 풀이' for k in keys}

    monkeypatch.setattr(app_module.ai, 'claude_bin', '/bin/true')
    monkeypatch.setattr(app_module.ai, 'backend', 'claude')
    monkeypatch.setattr(app_module.ai, 'get_group', fake_group)
    monkeypatch.setattr(app_module.ai, 'is_cached', lambda ctx: False)
    monkeypatch.setattr(app_module, 'quota', app_module.Quota())
    c = app.test_client()
    c.calls = calls
    return c


def _aid(html):
    m = re.search(r'var analysisId = "([^"]+)"', html)
    return m.group(1) if m else None


def test_index_has_new_title(client):
    html = client.get('/').get_data(as_text=True)
    assert '원구연-무료 사주풀이' in html
    assert '별하' not in html


def test_result_renders_chart(client):
    r = client.post('/result', data=FORM)
    html = r.get_data(as_text=True)
    assert r.status_code == 200
    for ch in ['庚', '午', '辛', '巳', '辰', '癸', '未']:   # 경오 신사 경진 계미
        assert ch in html
    assert '지금</span>' in html          # 현재 대운 표시
    assert '태양시' in html               # 계산 기준 표기
    assert _aid(html)


@pytest.mark.parametrize('field,value,msg', [
    ('name', '', '이름을'),
    ('gender', 'x', '성별을'),
    ('year', '1800', '1900년부터'),
    ('month', '2', None), ('day', '30', '존재하지 않는 날짜'),
    ('birth_time', '25:00', '태어난 시간'),
    ('region', 'mars', '출생 지역'),
])
def test_validation(client, field, value, msg):
    data = dict(FORM, **{field: value})
    if field == 'month':
        return
    if field == 'day':
        data['month'] = '2'
    r = client.post('/result', data=data)
    assert r.status_code == 400
    assert msg in r.get_data(as_text=True)


def test_error_message_is_escaped(client):
    r = client.post('/result', data=dict(FORM, name='<img src=x onerror=alert(1)>', year='abc'))
    html = r.get_data(as_text=True)
    assert r.status_code == 400
    assert '<img src=x' not in html and '&lt;img src=x' in html


def test_lunar_leap_input(client):
    r = client.post('/result', data=dict(FORM, calendar='lunar', year='2020', month='4', day='15', leap='1'))
    html = r.get_data(as_text=True)
    assert r.status_code == 200 and '음력 2020년 윤4월 15일' in html and '양력 2020-06-06' in html
    r = client.post('/result', data=dict(FORM, calendar='lunar', year='2021', month='4', day='1', leap='1'))
    assert r.status_code == 400 and '윤4월이 없습니다' in r.get_data(as_text=True)


def test_time_unknown_hides_hour(client):
    r = client.post('/result', data=dict(FORM, birth_time='', time_unknown='1'))
    html = r.get_data(as_text=True)
    assert r.status_code == 200
    assert '시주는 비워 두었습니다' in html
    assert html.count('<span class="unknown">?</span>') == 2   # 시주 천간·지지 두 칸이 비어 있다


def test_solar_time_checkbox_off(client):
    data = dict(FORM)
    data.pop('solar_time')
    html = client.post('/result', data=data).get_data(as_text=True)
    assert '보정 안 함' in html


def test_api_flow(client):
    aid = _aid(client.post('/result', data=FORM).get_data(as_text=True))
    for g in app_module.GROUPS:
        r = client.post(f'/api/analysis/{aid}/{g}')
        assert r.status_code == 200 and r.get_json()['group'] == g
    assert client.post(f'/api/analysis/{aid}/nope').status_code == 404
    assert client.post('/api/analysis/unknown-id/summary').status_code == 410


def test_quota_per_ip(client, monkeypatch):
    monkeypatch.setattr(app_module, 'LIMIT_PER_IP', 2)
    hdr = {'CF-Connecting-IP': '203.0.113.7'}
    states = []
    for _ in range(3):
        html = client.post('/result', data=FORM, headers=hdr).get_data(as_text=True)
        states.append(_aid(html) is not None)
    assert states == [True, True, False]
    assert '제공량' in html
    # 다른 IP는 영향 없음, 로컬 직접 접속은 무제한
    assert _aid(client.post('/result', data=FORM, headers={'CF-Connecting-IP': '198.51.100.1'}).get_data(as_text=True))
    assert all(_aid(client.post('/result', data=FORM).get_data(as_text=True)) for _ in range(3))


def test_quota_total(client, monkeypatch):
    monkeypatch.setattr(app_module, 'LIMIT_TOTAL', 2)
    got = [_aid(client.post('/result', data=FORM, headers={'CF-Connecting-IP': f'203.0.113.{i}'}).get_data(as_text=True)) is not None for i in range(3)]
    assert got == [True, True, False]


def test_cached_result_does_not_consume_quota(client, monkeypatch):
    monkeypatch.setattr(app_module, 'LIMIT_PER_IP', 1)
    monkeypatch.setattr(app_module.ai, 'is_cached', lambda ctx: True)
    hdr = {'CF-Connecting-IP': '203.0.113.9'}
    assert all(_aid(client.post('/result', data=FORM, headers=hdr).get_data(as_text=True)) for _ in range(3))


def test_healthz(client):
    assert client.get('/healthz').get_json()['ok'] is True


def test_form_posts_to_result(client):
    assert 'action="/result"' in client.get('/').get_data(as_text=True)
    assert client.post('/loading', data=FORM).status_code == 200


def test_error_marks_field(client):
    html = client.post('/result', data=dict(FORM, day='31', month='2')).get_data(as_text=True)
    assert html.count('aria-invalid="true"') == 3   # 년·월·일 세 칸
