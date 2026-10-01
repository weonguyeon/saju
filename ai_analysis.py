import os
import json
import shutil
import subprocess
import tempfile
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = "당신은 현대적 감각을 가진 사주 분석 전문가입니다. 반드시 JSON 형식으로만 답변하며, 값은 항상 문자열이어야 합니다."


class AIAnalysis:
    def __init__(self):
        # AI_BACKEND=claude(기본): 로컬 Claude Code CLI 구독으로 호출 / openai: 기존 GPT-4o API
        self.backend = os.getenv("AI_BACKEND", "claude").lower()
        self.client = None
        if self.backend == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key)
        else:
            self.claude_bin = os.getenv("CLAUDE_BIN") or shutil.which("claude")
            self.claude_model = os.getenv("CLAUDE_MODEL")  # 비우면 CLI 기본 모델
            self.timeout = int(os.getenv("CLAUDE_TIMEOUT", "600"))

    def get_deep_analysis(self, name, gender, pillars, ohaeng, ten_stars_list, current_daewun, birth_context):
        if self.backend == "openai" and not self.client:
            return None
        if self.backend != "openai" and not self.claude_bin:
            print("AI 분석 오류: claude CLI를 찾을 수 없습니다 (CLAUDE_BIN 설정 필요)")
            return None

        ohaeng_str = ", ".join([f"{k}({v}%)" for k, v in ohaeng['percentages'].items()])
        
        pillars_summary = (
            f"연:[{pillars['year']['gan']}{pillars['year']['zhi']}] "
            f"월:[{pillars['month']['gan']}{pillars['month']['zhi']}] "
            f"일:[{pillars['day']['gan']}{pillars['day']['zhi']}] "
            f"시:[{pillars['hour']['gan']}{pillars['hour']['zhi']}]"
        )
        
        day_stem = pillars['day']['gan']

        prompt = f"""
# Role: 2030 맞춤형 라이프 전략가 & 현대 명리학 마스터
당신은 사용자의 '{birth_context}'라는 생애 주기적 배경을 깊이 고려하여 조언하는 전문 분석가입니다.

# Input Data
- 이름: {name}, 성별: {gender}, 나이/생년: {birth_context}
- 본원(일간): {day_stem}
- 사주 원국: {pillars_summary}
- 십신 구성: {ten_stars_list}
- 오행 점수: {ohaeng_str}
- 현재 대운: {current_daewun}

# Analysis Roadmap & Output JSON Structure
모든 답변은 다음 키를 가진 JSON 형식으로 출력하세요. 각 필드는 예시처럼 **최소 8~12문장 이상의 풍부한 장문**으로, 사용자가 읽었을 때 전율이 느껴질 정도의 깊이 있는 서술형으로 작성하세요.

1. total_summary: [평생사주 총평] 삶의 목적, 전체적인 운의 흐름, 타고난 기질과 미래에 대한 낭만적인 통찰을 에세이처럼 서술하세요.
2. gmhs: [생애주기 분석] 근묘화실(년/월/일/시) 기반.
   - year: 초년기(0~19세) - 부모운, 성장 환경, 성격의 뿌리 (최소 5문장)
   - month: 청년기(20~39세) - 사회생활, 직업적 도전, 자아실현 (최소 5문장)
   - day: 중년기(40~59세) - 자산 형성, 인생의 꽃, 가정운 (최소 5문장)
   - hour: 말년기(60세~) - 결실, 자녀복, 노후의 평온함 (최소 5문장)
3. daewoon_trend: [대운의 흐름] 현재 대운({current_daewun})을 중심으로 10년 주기의 변화가 사용자 인생에 주는 의미와 다가올 기회에 대한 아주 상세하고 풍부한 서사.
   - 대운의 핵심 키워드나 슬로건을 포함할 것.
   - 10년의 흐름을 초반, 중반, 후반으로 나누어 스토리텔링 (최소 15~20문장 이상).
   - 직업, 재물, 대인관계 측면에서의 구체적이고 현실적인 행동 지침 포함.
4. health_analysis: [건강 & 체질] 오행 밸런스에 근거한 구체적인 신체적 특징, 취약 부위, 맞춤형 힐링 제안.
5. social_analysis: [사회운 & 적성] 대인관계 스타일, 조직 적응도, 추천 직업 군 및 성공 전략.
6. personality_deep: [인성 & 성향] 내면의 인품, 숨겨진 재능, 감정 다스리는 법에 대한 깊은 분석.
7. love_romance: [애정 & 인연] 연애 패턴, 배우자 복, 행복한 관계를 위한 조언.
8. wealth_strategy: [재물 운용 전략] 돈을 모으는 법, 투자 성향, 손실 방지 비책.
9. today_luck: [오늘의 에너지] 오늘 하루를 위한 강렬하고 따뜻한 격언.

# Instruction for Quality
1. [Tone]: 전문 용어(십성, 오행 등)를 현대적인 심리학 용어와 비유(예: 단단한 원석, 촉촉한 단비)로 풀어내어 공감을 극대화하세요.
2. [Volume]: 각 칸을 채우는 텍스트는 단순히 정보를 주는 게 아니라, 한 권의 자기계발서나 위로의 편지처럼 느껴지도록 풍성하게 작성하세요.
3. [Context]: 사용자의 연령({birth_context})을 고려하여 현재 가장 고민할 법한 지점을 정확히 짚어주세요.
"""

        if self.backend == "openai":
            return self._call_openai(prompt)
        return self._call_claude(prompt)

    def _call_claude(self, prompt):
        # 도구·설정·MCP를 모두 끄고 텍스트 생성만 하도록 헤드리스 호출 (프롬프트는 stdin으로 전달)
        cmd = [
            self.claude_bin, "-p",
            "--output-format", "json",
            "--tools", "",
            "--setting-sources", "",
            "--strict-mcp-config",
            "--no-session-persistence",
            "--system-prompt", SYSTEM_PROMPT + " 코드 블록 없이 JSON 객체 하나만 출력하세요.",
        ]
        if self.claude_model:
            cmd += ["--model", self.claude_model]
        try:
            # 프로젝트 폴더의 CLAUDE.md 등이 섞이지 않도록 빈 임시 폴더에서 실행
            with tempfile.TemporaryDirectory() as cwd:
                proc = subprocess.run(
                    cmd, input=prompt, capture_output=True, text=True,
                    timeout=self.timeout, cwd=cwd,
                )
            if proc.returncode != 0:
                print(f"AI 분석 오류: claude 종료 코드 {proc.returncode}\n{proc.stderr or proc.stdout}")
                return None
            envelope = json.loads(proc.stdout)
            if envelope.get("is_error"):
                print(f"AI 분석 오류: {envelope.get('result')}")
                return None
            return self._parse_json(envelope.get("result", ""))
        except Exception as e:
            print(f"AI 분석 오류: {e}")
            return None

    @staticmethod
    def _parse_json(text):
        # 모델이 ```json 펜스나 앞뒤 문장을 붙여도 첫 { ~ 마지막 } 구간만 파싱
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("응답에서 JSON 객체를 찾지 못했습니다")
        return json.loads(text[start:end + 1])

    def _call_openai(self, prompt):
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" },
                temperature=0.7,
                timeout=120
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"AI 분석 오류: {e}")
            return None
