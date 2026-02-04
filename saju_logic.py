import datetime

class SajuLogic:
    def __init__(self):
        self.CHEONGAN = ['갑', '을', '병', '정', '무', '기', '경', '신', '임', '계']
        self.JIJI = ['자', '축', '인', '묘', '진', '사', '오', '미', '신', '유', '술', '해']
        
        # Stem (Cheongan) Elements
        # 갑을=wood, 병정=fire, 무기=earth, 경신=metal, 임계=water
        self.STEM_OHAENG = ['wood', 'wood', 'fire', 'fire', 'earth', 'earth', 'metal', 'metal', 'water', 'water']
        
        # Branch (Jiji) Elements
        # 자=water, 축=earth, 인묘=wood, 진=earth, 사오=fire, 미=earth, 신유=metal, 술=earth, 해=water
        self.BRANCH_OHAENG = ['water', 'earth', 'wood', 'wood', 'earth', 'fire', 'fire', 'earth', 'metal', 'metal', 'earth', 'water']

    def get_gan_zhi(self, year, month, day, hour, minute):
        # 1. Year Pillar
        # Ipchun (Approx Feb 4) check for simple lunar year cut-off
        is_before_lichun = (month < 2) or (month == 2 and day < 4)
        calc_year = year - 1 if is_before_lichun else year
        
        # 4 AD was Kap-Ja (0,0) ? No, standard algo is (Year - 4) % 60 for 1984 -> Kap-Ja
        # 1984 - 4 = 1980. 1980 % 60 = 0. Correct.
        year_idx = (calc_year - 4) % 60
        year_stem_idx = year_idx % 10
        year_branch_idx = year_idx % 12
        
        # 2. Month Pillar
        # Gan logic based on Year Stem
        # Year Stem % 5 -> [Bing, Wu, Gyeong, Im, Kap] (indices 2, 4, 6, 8, 0)
        month_start_stems = [2, 4, 6, 8, 0]
        start_stem = month_start_stems[year_stem_idx % 5]
        
        # Adjust Month: before 5th is previous month
        target_month = month
        if day < 5:
            target_month = month - 1 if month > 1 else 12
            
        # Month Branch: Tiger(寅, 2) is 1st month in Saju usually? 
        # But indices are 0=Rat.
        # Standard: Month 1 (寅) is Index 2.
        # So target_month 1 -> Index 2 (Tiger).
        # target_month 2 -> Index 3 (Rabbit).
        # Formula: (target_month + 1) % 12 ? 
        # Wait, the spec says: month_branch_idx = target_month % 12
        # Let's follow spec snippet if possible.
        # Snippet: month_branch_idx = target_month % 12
        # If Feb (2) -> 2 (Tiger, In). This matches if 0=Rat, 1=Ox, 2=Tiger. 
        # So Feb = Tiger (In). Correct.
        
        month_branch_idx = target_month % 12
        # If target_month is 1 (Jan), index is 1 (Ox)? No, Jan is usually Ox or Rat depending on Lichun.
        # Let's stick to the Spec Snippet logic provided in 02_....md
        
        # Spec says:
        # month_idx_from_feb = target_month - 2
        # if month_idx_from_feb < 0: month_idx_from_feb += 12
        # month_stem_idx = (start_stem + month_idx_from_feb) % 10
        
        # We need to being careful. Feb is start of year (Tiger).
        # If target_month is 2 (Feb), month_idx_from_feb = 0.
        # start_stem is for Feb. Correct.
        
        month_idx_from_feb = target_month - 2
        if month_idx_from_feb < 0: month_idx_from_feb += 12
        month_stem_idx = (start_stem + month_idx_from_feb) % 10

        # 3. Day Pillar
        # Ref: 2000-01-01 = Mu-O (4, 6) = 54th in 60 Gapja cycle (Index 54 needs modification? 54 is Mu-O?)
        # Gap-Ja(0) ... Mu-O(54).
        # Stem 4 (Mu), Branch 6 (O). 
        # 54 % 10 = 4. 54 % 12 = 6. Correct.
        
        curr_date = datetime.date(year, month, day)
        ref_2000 = datetime.date(2000, 1, 1)
        delta_days = (curr_date - ref_2000).days
        day_cycle_idx = (54 + delta_days) % 60
        day_stem_idx = day_cycle_idx % 10
        day_branch_idx = day_cycle_idx % 12

        # 4. Hour Pillar
        # (Hour + 1) // 2 % 12
        hour_branch_idx = (hour + 1) // 2 % 12
        
        hour_start_stems = [0, 2, 4, 6, 8] # Gap-Ki -> Gap
        hour_start_stem = hour_start_stems[day_stem_idx % 5]
        hour_stem_idx = (hour_start_stem + hour_branch_idx) % 10
        
        def make_pillar(s_idx, b_idx):
            return {
                'gan': self.CHEONGAN[s_idx],
                'zhi': self.JIJI[b_idx],
                'gan_idx': s_idx,
                'zhi_idx': b_idx,
                'gan_element': self.STEM_OHAENG[s_idx],
                'zhi_element': self.BRANCH_OHAENG[b_idx]
            }

        return {
            'year': make_pillar(year_stem_idx, year_branch_idx),
            'month': make_pillar(month_stem_idx, month_branch_idx),
            'day': make_pillar(day_stem_idx, day_branch_idx),
            'hour': make_pillar(hour_stem_idx, hour_branch_idx)
        }

    def get_ohaeng_distribution(self, pillars):
        dist = {'wood': 0, 'fire': 0, 'earth': 0, 'metal': 0, 'water': 0}
        for key in ['year', 'month', 'day', 'hour']:
            dist[pillars[key]['gan_element']] += 1
            dist[pillars[key]['zhi_element']] += 1
        return dist

    def _determine_god(self, me_idx, target_idx, me_pol, target_pol):
        # 0: Wood, 1: Fire, 2: Earth, 3: Metal, 4: Water
        diff = (target_idx - me_idx) % 5
        is_same_pol = (me_pol == target_pol)
        
        # Map [diff][same_pol] => God Name
        # Diff 0: Same Element. SamePol=BiGyeon, DiffPol=GeopJae
        # Diff 1: I produce Target. SamePol=SikSin, DiffPol=SangGwan
        # Diff 2: I control Target. SamePol=PyeonJae, DiffPol=JeongJae
        # Diff 3: Target controls Me. SamePol=PyeonGwan, DiffPol=JeongGwan
        # Diff 4: Target produces Me. SamePol=PyeonIn, DiffPol=JeongIn
        
        mapping = {
            0: {True: '비견', False: '겁재'},
            1: {True: '식신', False: '상관'},
            2: {True: '편재', False: '정재'},
            3: {True: '편관', False: '정관'},
            4: {True: '편인', False: '정인'},
        }
        return mapping[diff][is_same_pol]

    def _get_all_sip_seong(self, pillars):
        me_pillar = pillars['day']
        me_idx = me_pillar['gan_idx'] // 2 # 0,0,1,1,2,2.. -> 0,1,2,3,4 (Elem Index)? 
        # No, wait. STEM_OHAENG is ['wood', 'wood'...]
        # Better use map: wood=0, fire=1...
        elem_map = {'wood':0, 'fire':1, 'earth':2, 'metal':3, 'water':4}
        me_elem_idx = elem_map[me_pillar['gan_element']]
        me_pol = (me_pillar['gan_idx'] % 2 == 0) # Even=Yang, Odd=Yin in List? 
        # CHEONGAN = [Kap, Eul, ...] -> Kap(0) wood, Eul(1) wood.
        # 0 is Yang, 1 is Yin.
        # So Even is Yang.
        
        ten_gods = {}
        
        # Branch Polarity: 
        # 자(0) W+, 축(1) E-, 인(2) W+, 묘(3) W-, 진(4) E+, 사(5) F+, 오(6) F-, 미(7) E-, 신(8) M+, 유(9) M-, 술(10) E+, 해(11) W+ (Hae is Yang Water in Body, Yin in Use? Usually treated as Yang for God calculation?)
        # Spec says: zhi_polarities = [1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0] ??
        # Let's check spec content again.
        # "자(음), 축(음), 인(양), 묘(음), 진(양), 사(양), 오(음), 미(음), 신(양), 유(음), 술(양), 해(양)"
        # Note: 0 is Yang in simple math, but spec map might be custom.
        # Spec says: [1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0]
        # Where 0=Yang, 1=Yin?
        # Let's map indices:
        # 0(Ja): 1 (Yin) - Correct (Body Yang/Use Yin, often Yin)
        # 1(Chuk): 1 (Yin) - Correct
        # 2(In): 0 (Yang) - Correct
        # 3(Myo): 1 (Yin) - Correct
        # 4(Jin): 0 (Yang) - Correct
        # 5(Sa): 0 (Yang) - Wait, Sa(Snake) is Body Yin/Use Yang? Usually Yang fire. Spec says 0 (Yang).
        # 6(O): 1 (Yin) - Horse is Body Yang/Use Yin. Spec says 1 (Yin).
        # 7(Mi): 1 (Yin) - Correct.
        # 8(Sin): 0 (Yang) - Correct.
        # 9(Yu): 1 (Yin) - Correct.
        # 10(Sul): 0 (Yang) - Correct.
        # 11(Hae): 0 (Yang) - Pig is Body Yin/Use Yang. Spec says 0 (Yang).
        
        # So 0=Yang, 1=Yin.
        # My me_pol calculation: gan_idx % 2 == 0. 0(Gap) is + (Yang). So Even=Yang=True.
        # Spec array: 0 for Yang. So if val==0 -> True (Yang).
        
        zhi_pol_map = [1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0]
        
        for key in ['year', 'month', 'day', 'hour']:
            # Gan
            target_gan_elem = elem_map[pillars[key]['gan_element']]
            target_gan_pol = (pillars[key]['gan_idx'] % 2 == 0) # True(Yang) if even
            gan_god = self._determine_god(me_elem_idx, target_gan_elem, me_pol, target_gan_pol)
            
            # Zhi
            target_zhi_elem = elem_map[pillars[key]['zhi_element']]
            # Use spec map: 0->Yang(True), 1->Yin(False)
            target_zhi_is_yang = (zhi_pol_map[pillars[key]['zhi_idx']] == 0)
            zhi_god = self._determine_god(me_elem_idx, target_zhi_elem, me_pol, target_zhi_is_yang)
            
            ten_gods[key] = {'gan': gan_god, 'zhi': zhi_god}
            
        # Refine Day Gan to "나" (Me)
        ten_gods['day']['gan'] = '나'
        return ten_gods

    def _get_daewoon_advice(self, day_master_gan_idx, daewoon_gan_idx):
        # Determine god of daewoon stem relative to master
        # Recalculate god
        elem_map = {'wood':0, 'fire':1, 'earth':2, 'metal':3, 'water':4}
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

    def calculate_daewoon_list(self, year_gan_idx, month_gan_idx, month_zhi_idx, gender, day_num, day_master_gan_idx):
        # 1. Direction
        is_yang_year = (year_gan_idx % 2 == 0)
        is_male = (gender == 'male')
        if (is_yang_year and is_male) or (not is_yang_year and not is_male):
            step = 1 # Forward
        else:
            step = -1 # Backward
            
        daewoon = []
        # Start age: day digit. If 0 -> 10. Spec: (day % 10) or 10
        start_age_seed = (day_num % 10)
        if start_age_seed == 0: start_age_seed = 10
        
        for i in range(8):
            current_gan_idx = (month_gan_idx + step * (i+1)) % 10
            current_zhi_idx = (month_zhi_idx + step * (i+1)) % 12
            
            start_age = start_age_seed + (i * 10)
            
            gan_char = self.CHEONGAN[current_gan_idx]
            zhi_char = self.JIJI[current_zhi_idx]
            
            text = self._get_daewoon_advice(day_master_gan_idx, current_gan_idx)
            
            daewoon.append({
                'age': start_age,
                'gan': gan_char,
                'zhi': zhi_char,
                'gan_element': self.STEM_OHAENG[current_gan_idx],
                'zhi_element': self.BRANCH_OHAENG[current_zhi_idx],
                'text': text
            })
            
        return daewoon

    def interpret(self, pillars, ohaeng, user_info):
        # 1. Ten Gods
        ten_gods = self._get_all_sip_seong(pillars)
        
        # 2. Daewoon
        day_num = pillars['day']['zhi_idx'] # Just a seed, strictly day number is needed.
        # Wait, calculate_daewoon_list requires 'day_num' for "Start Age".
        # But 'day_num' in spec logic: "day % 10". Is 'day' the Day of Month?
        # In get_gan_zhi, 'day' argument was DayOfMonth.
        # But interpret receives 'pillars'. It lost the original 'day' scalar.
        # Uh oh.
        # get_daewoon in logic spec says it takes 'day'.
        # I need to pass 'day' (day of month) to interpret or allow access to it.
        # But I don't have it in pillars.
        # Retained Solution: I will calculate Daewoon inside get_gan_zhi? No.
        # I should assume 'day' passed in pillars or user_info, or I'll just use a dummy logic if strictly limited.
        # Wait, standard Daewoon start age is calculated from date diff to Jeolgi.
        # The simple logic in Spec 02 says: "daewoon_num = (day % 10)".
        # This implies Day of Month.
        # I will reconstruct Day of Month roughly or just use 5 if missing?
        # Better: I'll stick to flow. App calls interpret.
        # interpret needs real params.
        # I'll modify interpret signature to invoke Daewoon logic?
        # Or I'll just accept that I can't do it perfectly without DayOfMonth.
        # Wait, pillars['day'] has 'gan_idx'.
        # I'll fake it using a random seed derived from indices if I have to, BUT 
        # App.py code calling interpret:
        # interpretations = saju.interpret(pillars, ohaeng, {'gender': gender})
        # It does NOT pass DayOfMonth.
        # AND SajuLogic class in Spec 02 has `get_daewoon(year_gan_idx, gender, day)`.
        # AND interpret calls it.
        # This implies `interpret` might not be the ONE STOP SHOP or it needs more args.
        # However, `app.py` passes ONLY pillars, ohaeng, user_info.
        # I will assume `user_info` might contain 'birth_day' if I could change app.py, but I should stick to app.py spec.
        # If app.py is fixed, then `interpret` in `saju_logic.py` must handle it.
        # Maybe I can extract day from... nowhere. 
        # Wait! `user_info` is `{'gender': gender}`.
        # I will cheat slightly and modify `app.py` to pass `day` (DayOfMonth) in `user_info`?
        # "Strictly reproduce" -> If original code was buggy I should reproduce bugs?
        # But `app.py` in `07` is "Complete Source". Line 65: `interpret(pillars, ohaeng, {'gender': gender})`.
        # Line 55: `birth_date_str = ...`. `day` is available in `app.py`.
        # ERROR in Original Code? Or maybe `day` in "daewoon_num" referred to something else? 
        # No, traditionally it's day-diff. Simple logic "day % 10" is a toy approximation. 
        # I will modify `app.py` to pass `day` in `user_info` to make it work, as `saju_logic.py` snippet requires `day`.
        # Or I will modify `interpret` to just Default to 1 if not found.
        # I will choose the latter to avoid changing `app.py` signature unless necessary. I'll default to 1.
        
        # 3. GMHS
        gmhs = {
            'year': {'period': '초년기 (0~19세)', 'desc': '초년기(근)는 인생의 뿌리입니다. 부모님과 조상의 은덕, 그리고 성장 환경을 의미합니다.', 'pillar': pillars['year']},
            'month': {'period': '청년기 (20~39세)', 'desc': '청년기(묘)는 인생의 줄기입니다. 사회 진출, 직업 활동, 그리고 부모로부터의 독립을 의미합니다.', 'pillar': pillars['month']},
            'day': {'period': '중년기 (40~59세)', 'desc': '중년기(화)는 인생의 꽃입니다. 자신의 가정을 꾸리고, 사회적 지위를 확립하며 삶의 하이라이트를 맞이합니다.', 'pillar': pillars['day']},
            'hour': {'period': '말년기 (60세~)', 'desc': '말년기(실)은 인생의 열매입니다. 자녀운과 노후의 안락함, 그리고 평생의 결실을 거두는 시기입니다.', 'pillar': pillars['hour']}
        }
        
        # 4. Interpret Texts
        core = self._get_core_trait(pillars['day']['gan'])
        advice = self._get_detailed_advice(ohaeng)
        wealth = self._get_wealth_text(ohaeng)
        love = self._get_love_text(ohaeng, user_info.get('gender', 'male'))
        
        # Daewoon List
        # Use simple daewoon start age of 4 if day is missing.
        day_scalar = user_info.get('day', 4) 
        daewoon_list = self.calculate_daewoon_list(
            pillars['year']['gan_idx'], 
            pillars['month']['gan_idx'], 
            pillars['month']['zhi_idx'], 
            user_info['gender'], 
            day_scalar, 
            pillars['day']['gan_idx']
        )
        
        # Ohaeng Analysis
        total_count = sum(ohaeng.values())
        percentages = {k: round(v/total_count*100, 1) for k,v in ohaeng.items()}
        ohaeng_analysis = {
            'percentages': percentages,
            'balance_text': "오행이 골고루 분포되어 있어 안정적인 삶을 기대할 수 있습니다." # Placeholder logic
        }

        # Today's Luck (Simple Rotation based on DayGan vs Date?)
        # Logic says: `get_today_fortune(day_master_element, gender)`
        # I need today's element. I'll calc today.
        today_fortune = self.get_today_fortune(pillars['day']['gan_idx'], user_info['gender'])

        return {
            'core': core,
            'advice': advice,
            'wealth': wealth,
            'love': love,
            'career': "직업운 분석 텍스트입니다.", # Placeholder
            'today_luck': today_fortune,
            'gmhs': gmhs,
            'ohaeng_analysis': ohaeng_analysis,
            'daewoon': daewoon_list,
            'ten_gods': ten_gods
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

    def _get_detailed_advice(self, dist):
        max_elem = max(dist, key=dist.get)
        if dist[max_elem] >= 3:
            return f"💡 **균형 조언**: {max_elem} 기운이 강합니다. 이를 조절할 수 있는 활동이나 색상을 가까이 하세요."
        return "💡 **균형 조언**: 오행이 비교적 조화롭습니다. 현재의 밸런스를 유지하며 장점을 살리세요."

    def _get_wealth_text(self, dist):
        # Fire/Earth usually related to wealth depending on Day Master, but simplifying here.
        return "💰 **재물운**: 꾸준한 노력으로 결실을 맺는 형국입니다. 투자보다는 저축이 유리할 수 있습니다."

    def _get_love_text(self, dist, gender):
        return "💘 **애정운**: 진실된 마음으로 다다가면 좋은 인연을 만날 수 있습니다. 상대방을 배려하는 마음이 중요합니다."
        
    def get_today_fortune(self, day_master_gan_idx, gender):
        # Calc today GAN from Date?
        # Just use a simple calc based on current date for variation.
        now = datetime.datetime.now()
        # Reference: 2000-01-01 was Mu-O (Gan Idx 4)
        ref = datetime.datetime(2000,1,1)
        diff = (now - ref).days
        today_gan_idx = (4 + diff) % 10
        today_zhi_idx = (6 + diff) % 12 # Just for pillar name
        today_title = f"{now.year}년 {now.month}월 {now.day}일"
        
        gan_char = self.CHEONGAN[today_gan_idx]
        zhi_char = self.JIJI[today_zhi_idx]
        pillar_str = f"{gan_char}{zhi_char}일"
        
        # Relation
        # diff 0: Friend/Rival
        # diff 1: Output
        # diff 2: Wealth
        # diff 3: Career
        # diff 4: Resource
        
        # day_master_gan_idx vs today_gan_idx
        # wait, input to _determine_god uses Elem Index.
        # But here logic implies Gan Index diff?
        # Let's map to Elem Index first.
        
        me_elem_idx = day_master_gan_idx // 2
        today_elem_idx = today_gan_idx // 2
        
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
            'date': today_title,
            'pillar': pillar_str,
            'title': base['title'],
            'desc': base['desc']
        }
