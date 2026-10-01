import datetime
from zoneinfo import ZoneInfo

from lunar_python import Solar

from lunar_python import Lunar, LunarMonth

KST = ZoneInfo("Asia/Seoul")  # IANA 시간대 DB — 1954~61년 UTC+8:30, 서머타임(1948~60·1987~88)까지 반영
UTC = datetime.timezone.utc
# lunar_python의 절기 시각은 북경시(UTC+8) 기준
BEIJING_OFFSET = datetime.timedelta(hours=8)

# 출생지 경도 (진태양시 대신 지방평균태양시 = UTC + 경도×4분)
REGIONS = {
    'seoul': ('서울·경기·인천', 126.98),
    'chuncheon': ('강원 영서(춘천)', 127.73),
    'gangneung': ('강원 영동(강릉)', 128.90),
    'daejeon': ('대전·충청', 127.38),
    'jeonju': ('전북(전주)', 127.15),
    'gwangju': ('광주·전남', 126.85),
    'daegu': ('대구·경북', 128.60),
    'busan': ('부산·울산·경남', 129.08),
    'jeju': ('제주', 126.53),
}
DEFAULT_REGION = 'seoul'

TWELVE_STAGES = ['장생', '목욕', '관대', '건록', '제왕', '쇠', '병', '사', '묘', '절', '태', '양']
# 각 천간의 장생 지지 인덱스 (양간은 순행, 음간은 역행)
CHANGSHENG_START = {0: 11, 1: 6, 2: 2, 3: 9, 4: 2, 5: 9, 6: 5, 7: 0, 8: 8, 9: 3}

# 지장간 (여기 → 중기 → 정기) — 국내 만세력에서 널리 쓰는 표
HIDDEN_STEMS = [
    ['임', '계'], ['계', '신', '기'], ['무', '병', '갑'], ['갑', '을'],
    ['을', '계', '무'], ['무', '경', '병'], ['병', '기', '정'], ['정', '을', '기'],
    ['무', '임', '경'], ['경', '신'], ['신', '정', '무'], ['무', '갑', '임'],
]

ZODIAC = ['쥐', '소', '호랑이', '토끼', '용', '뱀', '말', '양', '원숭이', '닭', '개', '돼지']

HANJA_TO_HANGUL = dict(zip(
    "甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥",
    "갑을병정무기경신임계자축인묘진사오미신유술해",
))

ELEMENT_KO = {'wood': '목(木)', 'fire': '화(火)', 'earth': '토(土)', 'metal': '금(金)', 'water': '수(水)'}

# 자시(23~01시) 처리: split = 야자시(23시대는 당일 일주·다음날 시간), next = 23시부터 다음날 일주
ZISHI_SECT = {'split': 2, 'next': 1}


class SajuLogic:
    def __init__(self):
        self.CHEONGAN = ['갑', '을', '병', '정', '무', '기', '경', '신', '임', '계']
        self.JIJI = ['자', '축', '인', '묘', '진', '사', '오', '미', '신', '유', '술', '해']

        # 천간 오행: 갑을=목, 병정=화, 무기=토, 경신=금, 임계=수
        self.STEM_OHAENG = ['wood', 'wood', 'fire', 'fire', 'earth', 'earth', 'metal', 'metal', 'water', 'water']

        # 지지 오행: 자=수, 축=토, 인묘=목, 진=토, 사오=화, 미=토, 신유=금, 술=토, 해=수
        self.BRANCH_OHAENG = ['water', 'earth', 'wood', 'wood', 'earth', 'fire', 'fire', 'earth', 'metal', 'metal', 'earth', 'water']

    # ------------------------------------------------------------------
    # 사주 원국
    # ------------------------------------------------------------------
    def _to_pillar(self, ganzhi_hanja):
        gan = HANJA_TO_HANGUL[ganzhi_hanja[0]]
        zhi = HANJA_TO_HANGUL[ganzhi_hanja[1]]
        s_idx = self.CHEONGAN.index(gan)
        b_idx = self.JIJI.index(zhi)
        return {
            'gan': gan,
            'zhi': zhi,
            'gan_idx': s_idx,
            'zhi_idx': b_idx,
            'gan_element': self.STEM_OHAENG[s_idx],
            'zhi_element': self.BRANCH_OHAENG[b_idx],
        }

    @staticmethod
    def _eight_char(dt, sect=2):
        ec = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, 0).getLunar().getEightChar()
        ec.setSect(sect)
        return ec

    @staticmethod
    def lunar_to_solar(year, month, day, leap=False):
        """음력 → 양력 날짜. 없는 윤달·날짜면 ValueError"""
        try:
            lm = LunarMonth.fromYm(year, -month if leap else month)
        except Exception:
            lm = None
        if lm is None:
            raise ValueError(f"{year}년에는 음력 {'윤' if leap else ''}{month}월이 없습니다.")
        if not 1 <= day <= lm.getDayCount():
            raise ValueError(f"{year}년 음력 {'윤' if leap else ''}{month}월은 {lm.getDayCount()}일까지입니다.")
        sol = Lunar.fromYmd(year, -month if leap else month, day).getSolar()
        return datetime.date(sol.getYear(), sol.getMonth(), sol.getDay())

    @staticmethod
    def resolve_time(local, solar_time=True, region=DEFAULT_REGION):
        """입력한 한국 시계 시각을 계산용 시각들로 바꾼다.

        - beijing: 절기 비교용 (실제 순간을 북경시로 표현)
        - clock: 일·시주용. 보정 시 지방평균태양시(UTC + 경도×4분) — 동경시·서머타임이 자동으로 걸러진다
        """
        aware = local.replace(tzinfo=KST)
        utc = aware.astimezone(UTC).replace(tzinfo=None)
        beijing = utc + BEIJING_OFFSET
        lon = REGIONS.get(region, REGIONS[DEFAULT_REGION])[1]
        if solar_time:
            clock = utc + datetime.timedelta(minutes=lon * 4)
        else:
            clock = local
        return {
            'utc_offset': aware.utcoffset(),
            'dst': bool(aware.dst()),
            'beijing': beijing,
            'clock': clock,
            'longitude': lon,
        }

    def get_gan_zhi(self, year, month, day, hour, minute, solar_time=True, zishi='split', region=DEFAULT_REGION):
        """양력 한국 시계 시각 기준 사주 네 기둥.

        - 연·월주: 실제 절기 시각 기준 (입춘·각 절입 시각을 분 단위로 비교)
        - 일·시주: 보정 시 출생지 태양시, 아니면 입력 시각 그대로
        """
        t = self.resolve_time(datetime.datetime(year, month, day, hour, minute), solar_time, region)
        sect = ZISHI_SECT.get(zishi, 2)

        ym = self._eight_char(t['beijing'])
        dh = self._eight_char(t['clock'], sect)

        return {
            'year': self._to_pillar(ym.getYear()),
            'month': self._to_pillar(ym.getMonth()),
            'day': self._to_pillar(dh.getDay()),
            'hour': self._to_pillar(dh.getTime()),
        }

    # ------------------------------------------------------------------
    # 지장간·12운성·세운
    # ------------------------------------------------------------------
    def hidden_stems(self, zhi_idx):
        """지장간 (여기 → 중기 → 정기 순)"""
        return list(HIDDEN_STEMS[zhi_idx])

    def twelve_stage(self, gan_idx, zhi_idx):
        """일간 기준 지지의 12운성"""
        start = CHANGSHENG_START[gan_idx]
        offset = (zhi_idx - start) % 12 if gan_idx % 2 == 0 else (start - zhi_idx) % 12
        return TWELVE_STAGES[offset]

    def ten_god_of(self, day_gan_idx, gan_idx=None, zhi_idx=None):
        elem_map = {'wood': 0, 'fire': 1, 'earth': 2, 'metal': 3, 'water': 4}
        me = elem_map[self.STEM_OHAENG[day_gan_idx]]
        me_pol = day_gan_idx % 2 == 0
        if gan_idx is not None:
            return self._determine_god(me, elem_map[self.STEM_OHAENG[gan_idx]], me_pol, gan_idx % 2 == 0)
        zhi_pol_map = [1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0]
        return self._determine_god(me, elem_map[self.BRANCH_OHAENG[zhi_idx]], me_pol, zhi_pol_map[zhi_idx] == 0)

    def year_pillar_of(self, year):
        """양력 연도의 세운 간지 (그해 입춘 이후 기준)"""
        idx = (year - 4) % 60
        return self._to_pillar("甲乙丙丁戊己庚辛壬癸"[idx % 10] + "子丑寅卯辰巳午未申酉戌亥"[idx % 12])

    def zodiac(self, pillars):
        return ZODIAC[pillars['year']['zhi_idx']]

    def get_ohaeng_distribution(self, pillars):
        dist = {'wood': 0, 'fire': 0, 'earth': 0, 'metal': 0, 'water': 0}
        for key in ['year', 'month', 'day', 'hour']:
            dist[pillars[key]['gan_element']] += 1
            dist[pillars[key]['zhi_element']] += 1
        return dist

    # ------------------------------------------------------------------
    # 십성
    # ------------------------------------------------------------------
    def _determine_god(self, me_idx, target_idx, me_pol, target_pol):
        # 오행 순서 0:목 1:화 2:토 3:금 4:수 — 차이로 생극 관계 판정
        # 0 같은 오행(비겁) / 1 내가 생함(식상) / 2 내가 극함(재성) / 3 나를 극함(관성) / 4 나를 생함(인성)
        diff = (target_idx - me_idx) % 5
        is_same_pol = (me_pol == target_pol)
        mapping = {
            0: {True: '비견', False: '겁재'},
            1: {True: '식신', False: '상관'},
            2: {True: '편재', False: '정재'},
            3: {True: '편관', False: '정관'},
            4: {True: '편인', False: '정인'},
        }
        return mapping[diff][is_same_pol]

    def _get_all_sip_seong(self, pillars):
        elem_map = {'wood': 0, 'fire': 1, 'earth': 2, 'metal': 3, 'water': 4}
        me_pillar = pillars['day']
        me_elem_idx = elem_map[me_pillar['gan_element']]
        me_pol = (me_pillar['gan_idx'] % 2 == 0)  # 짝수 인덱스 = 양간

        # 지지 음양(정기 기준): 0=양, 1=음 — 자(계)·오(정)는 음, 사(병)·해(임)는 양으로 본다
        zhi_pol_map = [1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0]

        ten_gods = {}
        for key in ['year', 'month', 'day', 'hour']:
            target_gan_elem = elem_map[pillars[key]['gan_element']]
            target_gan_pol = (pillars[key]['gan_idx'] % 2 == 0)
            gan_god = self._determine_god(me_elem_idx, target_gan_elem, me_pol, target_gan_pol)

            target_zhi_elem = elem_map[pillars[key]['zhi_element']]
            target_zhi_is_yang = (zhi_pol_map[pillars[key]['zhi_idx']] == 0)
            zhi_god = self._determine_god(me_elem_idx, target_zhi_elem, me_pol, target_zhi_is_yang)

            ten_gods[key] = {'gan': gan_god, 'zhi': zhi_god}

        ten_gods['day']['gan'] = '나'
        return ten_gods

    # ------------------------------------------------------------------
    # 대운
    # ------------------------------------------------------------------
    def _get_daewoon_advice(self, day_master_gan_idx, daewoon_gan_idx):
        elem_map = {'wood': 0, 'fire': 1, 'earth': 2, 'metal': 3, 'water': 4}
        me_elem = elem_map[self.STEM_OHAENG[day_master_gan_idx]]
        me_pol = (day_master_gan_idx % 2 == 0)
        target_elem = elem_map[self.STEM_OHAENG[daewoon_gan_idx]]
        target_pol = (daewoon_gan_idx % 2 == 0)

        god = self._determine_god(me_elem, target_elem, me_pol, target_pol)

        advices = {
            '비견': "나와 뜻을 같이하는 동료나 경쟁자가 나타나는 시기입니다. 협력을 통해 성취를 이룰 수 있으나, 독단적인 결정은 피하는 것이 좋습니다.",
            '겁재': "강한 경쟁 심리가 발동하거나 재물 운용에 주의가 필요한 시기입니다. 겉으로는 화려해 보일 수 있으나 내실을 다지는 지혜가 필요합니다.",
            '식신': "나의 재능과 기술을 마음껏 발휘하는 시기입니다. 자연스러운 의식주 안정이 따르며, 창의적인 활동이 큰 성과를 거둘 수 있습니다.",
            '상관': "변화를 추구하고 자신을 표현하려는 욕구가 강해집니다. 뛰어난 언변과 재치로 인정받을 수 있으나, 구설수를 조심해야 합니다.",
            '편재': "큰 재물을 다루거나 사업적인 기회가 찾아오는 시기입니다. 활동 무대가 넓어지며 역동적인 성과를 기대할 수 있습니다.",
            '정재': "안정적인 수입과 재물 축적이 이루어지는 시기입니다. 꼼꼼하고 성실한 태도로 인정을 받으며, 가정의 안정이 찾아옵니다.",
            '편관': "강한 책임감과 리더십을 발휘해야 하는 시기입니다. 난관이 있을 수 있으나 이를 극복하면 큰 명예와 권위를 얻게 됩니다.",
            '정관': "명예와 승진, 합격운이 따르는 시기입니다. 원칙을 준수하고 반듯한 생활을 함으로써 사회적 신용이 높아집니다.",
            '편인': "특수한 기술이나 철학, 종교적인 분야에 관심이 깊어집니다. 남들이 보지 못하는 이면을 꿰뚫어보는 직관력이 발달합니다.",
            '정인': "학문 탐구와 문서운이 좋은 시기입니다. 귀인의 도움을 받거나 자격증 취득, 계약 성사 등 긍정적인 결실이 있습니다."
        }
        return f"[{god}] {advices.get(god, '')}"

    def calculate_daewoon_list(self, birth, gender, day_master_gan_idx, count=10):
        """절기까지의 날짜 수로 대운 시작 시점을 구한다 (3일 = 1년, 순행·역행은 연간 음양 × 성별).

        반환 항목의 age는 시작 시점의 만 나이, start/end_year는 해당 대운이 걸치는 양력 연도.
        """
        ec = self._eight_char(self.resolve_time(birth)['beijing'])
        yun = ec.getYun(1 if gender == 'male' else 0)
        s = yun.getStartSolar()
        first_start = datetime.date(s.getYear(), s.getMonth(), s.getDay())

        daewoon = []
        for i, dy in enumerate(yun.getDaYun(count + 1)[1:]):
            start = _add_years(first_start, 10 * i)
            pillar = self._to_pillar(dy.getGanZhi())
            daewoon.append({
                'age': _full_age(birth.date(), start),
                'start_date': start,
                'start_year': start.year,
                'end_year': start.year + 9,
                'gan': pillar['gan'],
                'zhi': pillar['zhi'],
                'gan_element': pillar['gan_element'],
                'zhi_element': pillar['zhi_element'],
                'text': self._get_daewoon_advice(day_master_gan_idx, pillar['gan_idx']),
                'gan_god': self.ten_god_of(day_master_gan_idx, gan_idx=pillar['gan_idx']),
                'zhi_god': self.ten_god_of(day_master_gan_idx, zhi_idx=pillar['zhi_idx']),
                'stage': self.twelve_stage(day_master_gan_idx, pillar['zhi_idx']),
                'forward': yun.isForward(),
            })
        return daewoon

    @staticmethod
    def current_daewoon(daewoon_list, today):
        """오늘이 속한 대운 (첫 대운 시작 전이면 None)."""
        current = None
        for dw in daewoon_list:
            if dw['start_date'] <= today:
                current = dw
        return current

    # ------------------------------------------------------------------
    # 해석 묶음
    # ------------------------------------------------------------------
    def interpret(self, pillars, ohaeng, user_info):
        """user_info: gender(필수), birth(datetime, 대운 계산용), today(date, 선택)"""
        gender = user_info.get('gender', 'male')
        ten_gods = self._get_all_sip_seong(pillars)

        # 근묘화실
        gmhs = {
            'year': {'period': '초년기 (0~19세)', 'desc': '초년기(근)는 인생의 뿌리입니다. 부모님과 조상의 은덕, 그리고 성장 환경을 의미합니다.', 'pillar': pillars['year']},
            'month': {'period': '청년기 (20~39세)', 'desc': '청년기(묘)는 인생의 줄기입니다. 사회 진출, 직업 활동, 그리고 부모로부터의 독립을 의미합니다.', 'pillar': pillars['month']},
            'day': {'period': '중년기 (40~59세)', 'desc': '중년기(화)는 인생의 꽃입니다. 자신의 가정을 꾸리고, 사회적 지위를 확립하며 삶의 하이라이트를 맞이합니다.', 'pillar': pillars['day']},
            'hour': {'period': '말년기 (60세~)', 'desc': '말년기(실)은 인생의 열매입니다. 자녀운과 노후의 안락함, 그리고 평생의 결실을 거두는 시기입니다.', 'pillar': pillars['hour']}
        }

        today = user_info.get('today') or datetime.datetime.now(KST).date()
        daewoon_list = []
        current = None
        if user_info.get('birth'):
            daewoon_list = self.calculate_daewoon_list(user_info['birth'], gender, pillars['day']['gan_idx'])
            current = self.current_daewoon(daewoon_list, today)

        total_count = sum(ohaeng.values())
        percentages = {k: round(v / total_count * 100, 1) for k, v in ohaeng.items()}
        ohaeng_analysis = {
            'percentages': percentages,
            'balance_text': self._get_balance_text(ohaeng),
        }

        return {
            'core': self._get_core_trait(pillars['day']['gan']),
            'advice': self._get_detailed_advice(ohaeng),
            'wealth': self._get_wealth_text(ohaeng),
            'love': self._get_love_text(ohaeng, gender),
            'today_luck': self.get_today_fortune(pillars['day']['gan_idx'], gender, today),
            'gmhs': gmhs,
            'ohaeng_analysis': ohaeng_analysis,
            'daewoon': daewoon_list,
            'current_daewoon': current,
            'ten_gods': ten_gods,
        }

    def _get_core_trait(self, master_gan):
        traits = {
            '갑': "🌲 곧게 뻗은 소나무 (갑목)\n리더십이 강하고 추진력이 뛰어나며, 한번 결심하면 굽히지 않는 강직한 성품입니다.",
            '을': "🌿 강인한 생명력의 꽃 (을목)\n유연하고 적응력이 뛰어나며, 어떠한 환경에서도 살아남는 끈기와 생활력이 강합니다.",
            '병': "☀️ 세상을 비추는 태양 (병화)\n열정적이고 화려하며, 숨김없는 솔직함으로 주변 사람들에게 활력을 불어넣는 리더입니다.",
            '정': "🕯️ 은근하게 타오르는 촛불 (정화)\n따뜻하고 섬세하며, 남을 배려하는 헌신적인 마음과 예리한 통찰력을 겸비했습니다.",
            '무': "⛰️ 묵직한 태산 (무토)\n믿음직스럽고 포용력이 넓으며, 신용을 중시하여 주변 사람들로부터 깊은 신뢰를 받습니다.",
            '기': "🌱 비옥한 텃밭 (기토)\n실속 있고 현실적이며, 어머니와 같은 포용력으로 인재를 기르고 결실을 맺는 능력이 있습니다.",
            '경': "🪨 단단한 원석 (경금)\n의리가 강하고 결단력이 있으며, 공과 사가 분명하여 혁명적인 변화를 이끌어내는 힘이 있습니다.",
            '신': "💎 반짝이는 보석 (신금)\n섬세하고 예리하며, 남다른 미적 감각과 자존심으로 자신만의 분야에서 빛을 발합니다.",
            '임': "🌊 드넓은 바다 (임수)\n지혜롭고 유연하며, 깊은 속내와 포용력으로 세상을 넓게 바라보는 통찰력이 있습니다.",
            '계': "🌧️ 촉촉한 단비 (계수)\n총명하고 감수성이 풍부하며, 상황에 따라 변신하는 지혜와 부드러운 카리스마가 있습니다."
        }
        return traits.get(master_gan, "알 수 없음")

    def _get_balance_text(self, dist):
        missing = [ELEMENT_KO[k] for k, v in dist.items() if v == 0]
        strong = [ELEMENT_KO[k] for k, v in dist.items() if v >= 3]
        parts = []
        if strong:
            parts.append(f"{', '.join(strong)} 기운이 강하게 치우쳐 있습니다.")
        if missing:
            parts.append(f"{', '.join(missing)} 기운이 원국에 없어 보완이 필요합니다.")
        if not parts:
            return "오행이 골고루 분포되어 있어 안정적인 삶을 기대할 수 있습니다."
        return " ".join(parts)

    def _get_detailed_advice(self, dist):
        max_elem = max(dist, key=dist.get)
        if dist[max_elem] >= 3:
            return f"💡 균형 조언: {ELEMENT_KO[max_elem]} 기운이 강합니다. 이를 조절할 수 있는 활동이나 색상을 가까이 하세요."
        return "💡 균형 조언: 오행이 비교적 조화롭습니다. 현재의 밸런스를 유지하며 장점을 살리세요."

    def _get_wealth_text(self, dist):
        return "💰 재물운: 꾸준한 노력으로 결실을 맺는 형국입니다. 투자보다는 저축이 유리할 수 있습니다."

    def _get_love_text(self, dist, gender):
        return "💘 애정운: 진실된 마음으로 다가가면 좋은 인연을 만날 수 있습니다. 상대방을 배려하는 마음이 중요합니다."

    def get_today_fortune(self, day_master_gan_idx, gender, today=None):
        # 오늘(한국 날짜)의 일진과 일간의 생극 관계로 오늘의 기운을 정한다
        today = today or datetime.datetime.now(KST).date()
        ec = self._eight_char(datetime.datetime(today.year, today.month, today.day, 12, 0))
        pillar = self._to_pillar(ec.getDay())

        me_elem_idx = day_master_gan_idx // 2
        today_elem_idx = pillar['gan_idx'] // 2
        rel_diff = (today_elem_idx - me_elem_idx) % 5

        fortunes = {
            0: {"title": "🤝 어깨를 나란히 하는 날", "desc": "주변 사람들과 협력하면 좋은 성과가 있습니다. 친구나 동료와의 만남이 즐거운 하루입니다."},
            1: {"title": "🎨 재능이 꽃피는 날", "desc": "창의력이 솟아나고 표현력이 좋아지는 날입니다. 새로운 아이디어를 내거나 취미 생활을 즐겨보세요."},
            2: {"title": "💰 결실을 맺는 날", "desc": "노력한 만큼 보상이 따르는 날입니다. 금전적인 이득이나 뜻밖의 선물이 있을 수 있습니다."},
            3: {"title": "👑 명예가 드높은 날", "desc": "책임감 있는 행동으로 인정받는 하루입니다. 직장에서 칭찬을 듣거나 승진의 기운이 있습니다."},
            4: {"title": "📚 귀인의 도움이 있는 날", "desc": "마음이 편안하고 문서운이 좋은 날입니다. 윗사람의 도움을 받거나 배움의 즐거움을 느낄 수 있습니다."}
        }
        base = fortunes[rel_diff]
        return {
            'date': f"{today.year}년 {today.month}월 {today.day}일",
            'pillar': f"{pillar['gan']}{pillar['zhi']}일",
            'title': base['title'],
            'desc': base['desc'],
        }


def _add_years(d, years):
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # 2월 29일
        return d.replace(year=d.year + years, day=28)


def _full_age(birth, on):
    """on 날짜 기준 만 나이"""
    return on.year - birth.year - ((on.month, on.day) < (birth.month, birth.day))
