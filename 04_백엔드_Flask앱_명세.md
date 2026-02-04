# Flask 앱 명세서 (app.py)

## 📌 개요

Flask 웹 애플리케이션의 라우팅, 데이터 처리, 템플릿 렌더링을 담당합니다.

---

## 🔧 초기화

```python
from flask import Flask, render_template, request
from saju_logic import SajuLogic
from ai_analysis import AIAnalysis
from datetime import datetime

app = Flask(__name__)
saju = SajuLogic()
ai = AIAnalysis()
```

---

## 🛣️ 라우트 정의

### GET `/` - 입력 페이지
```python
@app.route('/')
def index():
    return render_template('index.html')
```

### POST `/loading` - 로딩 페이지
```python
@app.route('/loading', methods=['POST'])
def loading():
    return render_template('loading.html', data=request.form)
```
- 폼 데이터를 그대로 `loading.html`에 전달
- 숨겨진 폼으로 300ms 후 자동 제출

### POST `/result` - 결과 페이지
```python
@app.route('/result', methods=['POST'])
def result():
    # 1. 폼 데이터 파싱
    name = request.form.get('name')
    gender = request.form.get('gender')
    birth_date_str = request.form.get('birth_date')  # "YYYY-MM-DD"
    birth_time_str = request.form.get('birth_time')  # "HH:MM"
    
    # 2. 날짜/시간 분리
    year, month, day = map(int, birth_date_str.split('-'))
    hour, minute = map(int, birth_time_str.split(':'))
    
    # 3. 사주 계산
    pillars = saju.get_gan_zhi(year, month, day, hour, minute)
    ohaeng = saju.get_ohaeng_distribution(pillars)
    interpretations = saju.interpret(pillars, ohaeng, {'gender': gender})
    
    # 4. 나이 계산
    age = datetime.now().year - year + 1
    birth_context = f"{year}년생 ({age}세)"
    
    # 5. AI용 십성 통계
    ten_gods_all = []
    for p_key in interpretations['ten_gods']:
        ten_gods_all.append(interpretations['ten_gods'][p_key]['gan'])
        ten_gods_all.append(interpretations['ten_gods'][p_key]['zhi'])
    
    from collections import Counter
    counts = Counter(ten_gods_all)
    ten_stars_list = ", ".join([f"{k} {v}" for k, v in counts.items()])
    
    # 6. 현재 대운 정보
    current_daewun = f"{interpretations['daewoon'][0]['age']}세 대운 ({interpretations['daewoon'][0]['gan']}{interpretations['daewoon'][0]['zhi']})"
    
    # 7. AI 분석 호출
    ai_data = ai.get_deep_analysis(
        name, gender, pillars,
        interpretations['ohaeng_analysis'],
        ten_stars_list,
        current_daewun,
        birth_context
    )
    
    # 8. AI 결과 병합
    if ai_data:
        interpretations['total_summary'] = ai_data.get('total_summary', "...")
        interpretations['personality_deep'] = ai_data.get('personality_deep', "...")
        interpretations['social_analysis'] = ai_data.get('social_analysis', "...")
        interpretations['health_analysis'] = ai_data.get('health_analysis', "...")
        interpretations['daewoon_trend'] = ai_data.get('daewoon_trend', "...")
        interpretations['love_romance'] = ai_data.get('love_romance', interpretations['love'])
        interpretations['wealth_strategy'] = ai_data.get('wealth_strategy', interpretations['wealth'])
        interpretations['core'] = ai_data.get('personality_deep', interpretations['core'])
        interpretations['advice'] = ai_data.get('health_analysis', interpretations['advice'])
        
        # GMHS 병합
        if 'gmhs' in ai_data:
            for period in ['year', 'month', 'day', 'hour']:
                if period in ai_data['gmhs']:
                    interpretations['gmhs'][period]['desc'] = ai_data['gmhs'][period]
        
        # 오늘의 운세 병합
        if 'today_luck' in ai_data:
            interpretations['today_luck']['desc'] = str(ai_data['today_luck'])
    
    # 9. 렌더링
    return render_template('result.html',
        name=name,
        pillars=pillars,
        ohaeng=ohaeng,
        interp=interpretations
    )
```

---

## 📊 템플릿 변수

### result.html에 전달되는 변수

| 변수명 | 타입 | 설명 |
|--------|------|------|
| `name` | str | 사용자 이름 |
| `pillars` | dict | 사주 원국 (year/month/day/hour) |
| `ohaeng` | dict | 오행 분포 (wood/fire/earth/metal/water 카운트) |
| `interp` | dict | 해석 데이터 전체 |

### interp 객체 구조

```python
{
    'core': '핵심 성향',
    'advice': '맞춤 조언',
    'wealth': '재물운',
    'wealth_strategy': 'AI 재물 전략',
    'love': '애정운',
    'love_romance': 'AI 애정 분석',
    'career': '직업 적성',
    'total_summary': 'AI 총평',
    'personality_deep': 'AI 성향 분석',
    'social_analysis': 'AI 사회운',
    'health_analysis': 'AI 건강 분석',
    'daewoon_trend': 'AI 대운 흐름',
    'today_luck': {
        'date': '2026년 01월 09일',
        'pillar': '갑자일',
        'title': '🤝 어깨를 나란히 하는 날',
        'desc': '...'
    },
    'gmhs': {
        'year': {'period': '초년기 (0~19세)', 'desc': '...', 'pillar': {...}},
        'month': {...},
        'day': {...},
        'hour': {...}
    },
    'ohaeng_analysis': {
        'percentages': {'wood': 25.0, 'fire': 12.5, ...},
        'details': [...],
        'balance_text': '오행이 골고루 갖춰진 황금 밸런스입니다!'
    },
    'daewoon': [
        {'age': 5, 'gan': '을', 'zhi': '축', 'gan_element': 'wood', 'zhi_element': 'earth', 'text': '[비견] ...'},
        # ... 8개
    ],
    'ten_gods': {
        'year': {'gan': '편인', 'zhi': '정재'},
        'month': {'gan': '비견', 'zhi': '식신'},
        'day': {'gan': '나', 'zhi': '편관'},
        'hour': {'gan': '상관', 'zhi': '정인'}
    }
}
```

---

## 🔄 에러 처리

```python
except Exception as e:
    import traceback
    traceback.print_exc()
    return f"Error occurred: {str(e)}", 400
```

---

## 🚀 실행

```python
if __name__ == '__main__':
    app.run(debug=True)
```

- 기본 포트: 5000
- 디버그 모드: 활성화
