"""구성학(九星)과 택일 — lunar_python 내장 역법 데이터 사용

宜·忌, 황도·흑도, 건제12신, 28수는 중국 《협기변방서》 계열 규칙이라 학파에 따라 결과가 다를 수 있다.
손없는날은 한국 민속 규칙(음력 끝자리 9·0일, 한국민족문화대백과 「손」 항목)으로 따로 계산한다.
"""
import datetime
from functools import lru_cache

from lunar_python import Solar

# 구성(九星)
NINE_STAR_KO = {
    '一白': ('일백수성', '수(水)', '유연하고 사려 깊으며, 사람 사이를 잇는 힘이 있습니다.'),
    '二黑': ('이흑토성', '토(土)', '성실하고 참을성이 강해, 맡은 일을 끝까지 돌봅니다.'),
    '三碧': ('삼벽목성', '목(木)', '추진력과 표현력이 좋아 새 일을 여는 데 강합니다.'),
    '四绿': ('사록목성', '목(木)', '부드럽고 신용을 중시해, 관계를 넓히며 성장합니다.'),
    '五黄': ('오황토성', '토(土)', '중심에 서는 기운으로, 지도력과 고집이 함께 큽니다.'),
    '六白': ('육백금성', '금(金)', '책임감과 원칙이 분명해 조직을 이끄는 힘이 있습니다.'),
    '七赤': ('칠적금성', '금(金)', '사교적이고 말솜씨가 좋아 즐거움을 만드는 사람입니다.'),
    '八白': ('팔백토성', '토(土)', '꾸준히 쌓아 올리는 힘이 있고, 변화의 전환점을 잘 잡습니다.'),
    '九紫': ('구자화성', '화(火)', '밝고 직관이 빠르며, 드러나 주목받는 자리에서 빛납니다.'),
}

ZHI_XING_KO = dict(zip('建除满平定执破危成收开闭', ['건', '제', '만', '평', '정', '집', '파', '위', '성', '수', '개', '폐']))
TIAN_SHEN_KO = {
    '青龙': '청룡', '明堂': '명당', '天刑': '천형', '朱雀': '주작', '金匮': '금궤', '天德': '천덕',
    '白虎': '백호', '玉堂': '옥당', '天牢': '천뢰', '玄武': '현무', '司命': '사명', '勾陈': '구진',
}
XIU_KO = dict(zip('角亢氐房心尾箕斗牛女虚危室壁奎娄胃昴毕觜参井鬼柳星张翼轸',
                  ['각', '항', '저', '방', '심', '미', '기', '두', '우', '여', '허', '위', '실', '벽', '규', '루', '위', '묘',
                   '필', '자', '삼', '정', '귀', '류', '성', '장', '익', '진']))
ZODIAC_KO = {'鼠': '쥐', '牛': '소', '虎': '호랑이', '兔': '토끼', '龙': '용', '蛇': '뱀', '马': '말', '羊': '양',
             '猴': '원숭이', '鸡': '닭', '狗': '개', '猪': '돼지'}
BRANCH_HANJA = '子丑寅卯辰巳午未申酉戌亥'

# 宜·忌 용어 (2019~2027년 실제 출현 114개 전부 — tests/test_almanac.py 가 빠짐을 검사)
YIJI_KO = {
    '安葬': '장례', '祭祀': '제사', '嫁娶': '결혼', '入宅': '입주', '动土': '땅 파기·착공', '开市': '개업',
    '出行': '여행·외출', '安床': '침대 들이기', '祈福': '기도·복 빌기', '移徙': '이사', '破土': '묘 터 파기',
    '开光': '불상·신상 모시기', '入殓': '입관', '作灶': '부엌 고치기', '纳采': '약혼 예물', '移柩': '운구',
    '解除': '청소·액막이', '修造': '집 수리', '栽种': '나무·작물 심기', '上梁': '상량', '馀事勿取': '그 밖의 일은 피함',
    '拆卸': '철거', '交易': '거래', '启钻': '묘 이장', '立券': '계약', '订盟': '약혼·약속', '除服': '탈상',
    '纳畜': '가축 들이기', '出火': '신위 옮기기', '成服': '상복 입기', '求嗣': '자녀 기원', '伐木': '벌목',
    '会亲友': '친척·친구 모임', '诸事不宜': '모든 일에 좋지 않음', '进人口': '사람 들이기(채용·입양)', '沐浴': '목욕재계',
    '裁衣': '옷 짓기', '安门': '문 달기', '冠笄': '성년식', '纳财': '재물 들이기', '斋醮': '재 올리기', '掘井': '우물 파기',
    '起基': '기초 공사', '塑绘': '조각·그림', '治病': '치료', '理发': '이발', '牧养': '가축 기르기', '谢土': '터 고사',
    '无': '없음', '挂匾': '현판 걸기', '扫舍': '대청소', '立碑': '비석 세우기', '作梁': '대들보 만들기', '坏垣': '담 허물기',
    '修坟': '묘 손질', '竖柱': '기둥 세우기', '盖屋': '지붕 덮기', '破屋': '집 허물기', '结网': '그물 짜기',
    '安香': '향단 모시기', '造畜稠': '축사 짓기', '安机械': '기계 설치', '捕捉': '사냥·포획', '塞穴': '구멍 막기',
    '赴任': '부임', '行丧': '장례 행렬', '合帐': '휘장 만들기', '求医': '진료 받기', '平治道涂': '길 닦기',
    '开池': '연못 파기', '经络': '베 짜기', '放水': '물 대기', '置产': '부동산 구입', '造庙': '사당 짓기',
    '修饰垣墙': '담장 손질', '畋猎': '사냥', '补垣': '담 보수', '开仓': '창고 열기', '探病': '병문안',
    '造仓': '창고 짓기', '入学': '입학', '取渔': '고기잡이', '造船': '배 만들기', '整手足甲': '손발톱 손질',
    '定磉': '주춧돌 놓기', '造桥': '다리 놓기', '架马': '작업대 설치', '词讼': '소송', '开生坟': '생전 묘 만들기',
    '针灸': '침뜸', '教牛马': '가축 길들이기', '开厕': '화장실 만들기', '筑堤': '둑 쌓기', '开柱眼': '기둥 구멍 내기',
    '出货财': '재물 내보내기', '开渠': '도랑 파기', '合寿木': '관 짜기', '酬神': '감사 제사', '纳婿': '데릴사위',
    '安碓磑': '방아 설치', '造车器': '수레 만들기', '习艺': '기술 배우기', '分居': '분가', '雕刻': '조각',
    '合脊': '용마루 올리기', '断蚁': '개미 막기', '普渡': '천도재', '割蜜': '꿀 따기', '问名': '혼담 묻기',
    '雇佣': '사람 고용', '乘船': '배 타기', '归岫': '돌아오기', '归宁': '친정 나들이', '修门': '문 고치기',
}

# 목적별로 볼 宜 용어
PURPOSES = {
    'move': ('이사', ['移徙', '入宅']),
    'wedding': ('결혼', ['嫁娶']),
    'open': ('개업', ['开市']),
    'contract': ('계약', ['立券', '交易']),
}


def nine_star(lunar_obj, kind='year'):
    # sect=3: 입춘·절입 '시각' 기준 (기본 sect=2 는 그날 0시부터 바뀌어 사주 연·월주와 어긋난다)
    star = lunar_obj.getYearNineStar(3) if kind == 'year' else lunar_obj.getMonthNineStar(3)
    key = star.toString()[:2]
    name, elem, desc = NINE_STAR_KO[key]
    return {'key': key, 'name': name, 'element': elem, 'desc': desc, 'number': '一二三四五六七八九'.index(key[0]) + 1}


def birth_stars(birth_beijing):
    """출생 본명성(연)·월명성. 절기 비교용 북경시 출생 시각을 받는다 (입춘·절입 기준)"""
    b = birth_beijing
    lunar_obj = Solar.fromYmdHms(b.year, b.month, b.day, b.hour, b.minute, 0).getLunar()
    return {'year': nine_star(lunar_obj, 'year'), 'month': nine_star(lunar_obj, 'month')}


def _ko_terms(terms):
    return [YIJI_KO.get(t, t) for t in terms]


def day_info(date, user_branch=None):
    """하루 택일 정보. user_branch: 사용자 연지 인덱스(0=자) — 그날 일지가 충하면 표시"""
    lunar_obj = Solar.fromYmd(date.year, date.month, date.day).getLunar()
    lunar_day = lunar_obj.getDay()
    yi, ji = lunar_obj.getDayYi(), lunar_obj.getDayJi()
    day_branch = BRANCH_HANJA.index(lunar_obj.getDayZhi())
    clash_user = user_branch is not None and (day_branch - user_branch) % 12 == 6
    tian_shen_type = lunar_obj.getDayTianShenType()
    return {
        'date': date,
        'weekday': '월화수목금토일'[date.weekday()],
        'lunar': f"{'윤' if lunar_obj.getMonth() < 0 else ''}{abs(lunar_obj.getMonth())}.{lunar_day}",
        'son_eomneun': lunar_day % 10 in (9, 0),
        'hwangdo': tian_shen_type == '黄道',
        'tian_shen': TIAN_SHEN_KO.get(lunar_obj.getDayTianShen(), lunar_obj.getDayTianShen()),
        'zhi_xing': ZHI_XING_KO.get(lunar_obj.getZhiXing(), lunar_obj.getZhiXing()),
        'xiu': XIU_KO.get(lunar_obj.getXiu(), lunar_obj.getXiu()),
        'xiu_luck': '길' if lunar_obj.getXiuLuck() == '吉' else '흉',
        'yi': _ko_terms(yi),
        'ji': _ko_terms(ji),
        'yi_raw': yi,
        'ji_raw': ji,
        'chong': ZODIAC_KO.get(lunar_obj.getDayChongShengXiao(), lunar_obj.getDayChongShengXiao()),
        'clash_user': clash_user,
    }


@lru_cache(maxsize=64)
def good_days(start, days=60, user_branch=None):
    """목적별 길일: 그 일이 宜에 있고 忌에 없으며, 황도일이고, 사용자 띠와 충하지 않는 날"""
    infos = [day_info(start + datetime.timedelta(days=i), user_branch) for i in range(days)]
    picks = {}
    for key, (label, terms) in PURPOSES.items():
        hits = []
        for d in infos:
            if any(t in d['yi_raw'] for t in terms) and not any(t in d['ji_raw'] for t in terms) \
                    and d['hwangdo'] and not d['clash_user']:
                hits.append(d)
        picks[key] = {'label': label, 'days': hits[:6]}
    return tuple(infos), picks
