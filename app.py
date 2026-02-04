from flask import Flask, render_template, request
from saju_logic import SajuLogic
from ai_analysis import AIAnalysis
from datetime import datetime

app = Flask(__name__)
saju = SajuLogic()
ai = AIAnalysis()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/loading', methods=['POST'])
def loading():
    return render_template('loading.html', data=request.form)

@app.route('/result', methods=['POST'])
def result():
    name = request.form.get('name')
    gender = request.form.get('gender')
    birth_date_str = request.form.get('birth_date')
    birth_time_str = request.form.get('birth_time')
    
    try:
        year, month, day = map(int, birth_date_str.split('-'))
        hour, minute = map(int, birth_time_str.split(':'))
        
        pillars = saju.get_gan_zhi(year, month, day, hour, minute)
        ohaeng = saju.get_ohaeng_distribution(pillars)
        interpretations = saju.interpret(pillars, ohaeng, {'gender': gender})
        
        now = datetime.now()
        age = now.year - year + 1
        birth_context = f"{year}년생 ({age}세)"
        
        ten_gods_all = []
        for p_key in interpretations['ten_gods']:
            ten_gods_all.append(interpretations['ten_gods'][p_key]['gan'])
            ten_gods_all.append(interpretations['ten_gods'][p_key]['zhi'])
        
        from collections import Counter
        counts = Counter(ten_gods_all)
        ten_stars_list = ", ".join([f"{k} {v}" for k, v in counts.items()])
        
        current_daewun = f"{interpretations['daewoon'][0]['age']}세 대운 ({interpretations['daewoon'][0]['gan']}{interpretations['daewoon'][0]['zhi']})"

        ai_data = ai.get_deep_analysis(
            name, gender, pillars, 
            interpretations['ohaeng_analysis'], 
            ten_stars_list, 
            current_daewun,
            birth_context
        )
        
        if ai_data:
            interpretations['total_summary'] = ai_data.get('total_summary', "평생 운세 데이터를 생성 중입니다.")
            interpretations['personality_deep'] = ai_data.get('personality_deep', "성향 분석 데이터를 생성 중입니다.")
            interpretations['social_analysis'] = ai_data.get('social_analysis', "사회운 분석 데이터를 생성 중입니다.")
            interpretations['health_analysis'] = ai_data.get('health_analysis', "건강 분석 데이터를 생성 중입니다.")
            interpretations['daewoon_trend'] = ai_data.get('daewoon_trend', "대운의 흐름 분석 데이터를 생성 중입니다.")
            interpretations['love_romance'] = ai_data.get('love_romance', interpretations['love'])
            interpretations['wealth_strategy'] = ai_data.get('wealth_strategy', interpretations['wealth'])
            
            interpretations['core'] = ai_data.get('personality_deep', interpretations['core']) 
            interpretations['advice'] = ai_data.get('health_analysis', interpretations['advice'])
            
            if 'gmhs' in ai_data and isinstance(ai_data['gmhs'], dict):
                for period in ['year', 'month', 'day', 'hour']:
                    if period in ai_data['gmhs'] and period in interpretations['gmhs']:
                        interpretations['gmhs'][period]['desc'] = ai_data['gmhs'][period]
            
            if 'today_luck' in ai_data:
                interpretations['today_luck']['desc'] = str(ai_data['today_luck'])

        return render_template('result.html', 
                               name=name, 
                               gender=gender,
                               birth_date=birth_date_str,
                               birth_time=birth_time_str,
                               pillars=pillars, 
                               ohaeng=ohaeng, 
                               interp=interpretations)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Error occurred: {str(e)}", 400

if __name__ == '__main__':
    app.run(debug=True)
