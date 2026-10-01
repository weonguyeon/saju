# 별하 (Byeolha) - 사주풀이 프로그램

<p align="center">
  <strong>당신의 운명을 비추는 별 ✨</strong>
</p>

---

## 📖 소개

**별하(Byeolha)**는 AI 기반 심층 사주 분석 웹 서비스입니다. 전통 명리학의 사주팔자 계산과 현대적인 AI 분석(기본 Claude Code CLI, 선택 GPT-4o)을 결합하여, 풍부하고 개인화된 운세 분석을 제공합니다.

---

## ✨ 주요 기능

- **사주 원국 계산**: 년/월/일/시주 자동 계산
- **오행 분석**: 목/화/토/금/수 분포 및 밸런스 진단
- **십성 판정**: 8개 글자의 십신(십성) 관계 분석
- **대운 분석**: 10년 주기 8회 = 80년 운세
- **근묘화실**: 생애 4단계 (초년/청년/중년/말년) 분석
- **오늘의 운세**: 일간 기반 맞춤 운세
- **AI 심층 분석**: Claude Code CLI(기본) 또는 GPT-4o 기반 장문 해석

---

## 🚀 빠른 시작

```bash
# 1. 패키지 설치
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# 2. AI 연결 — 기본은 로그인된 Claude Code CLI(claude) 구독을 그대로 사용, API 키 불필요
#    OpenAI로 돌리려면: echo -e "AI_BACKEND=openai\nOPENAI_API_KEY=sk-..." > .env

# 3. 서버 시작 (맥은 5000번을 AirPlay가 쓰므로 5050)
.venv/bin/python -c "from app import app; app.run(port=5050)"

# 4. 브라우저 접속
# http://127.0.0.1:5050
```

---

## 📁 프로젝트 구조

```
├── app.py              # Flask 메인 앱
├── saju_logic.py       # 사주 계산 로직
├── ai_analysis.py      # AI 분석 (Claude CLI / GPT-4o)
├── requirements.txt    # 의존성
├── .env                # API 키
├── static/
│   └── style.css       # 스타일
└── templates/
    ├── index.html      # 입력 폼
    ├── loading.html    # 로딩 화면
    └── result.html     # 결과 화면
```

---

## 📄 명세 문서

| 문서 | 설명 |
|------|------|
| [01_프로젝트_개요.md](01_프로젝트_개요.md) | 프로젝트 구조 및 실행 방법 |
| [02_백엔드_사주로직_명세.md](02_백엔드_사주로직_명세.md) | saju_logic.py 알고리즘 |
| [03_백엔드_AI분석_명세.md](03_백엔드_AI분석_명세.md) | GPT 프롬프트 및 응답 구조 |
| [04_백엔드_Flask앱_명세.md](04_백엔드_Flask앱_명세.md) | 라우팅 및 데이터 흐름 |
| [05_프론트엔드_UI명세.md](05_프론트엔드_UI명세.md) | HTML/CSS 상세 명세 |
| [06_데이터구조_명세.md](06_데이터구조_명세.md) | 코드 간 데이터 구조 |
| [07_전체_소스코드.md](07_전체_소스코드.md) | 완전한 소스코드 |

---

## 🛠️ 기술 스택

- **Backend**: Python Flask
- **AI**: Claude Code CLI 헤드리스(`claude -p`, 기본) / OpenAI GPT-4o(선택)
- **Calendar**: korean-lunar-calendar
- **Frontend**: HTML5, CSS3, JavaScript
- **Chart**: Chart.js (레이더 차트)
- **Font**: Pretendard
- **Icons**: Font Awesome 6.0

---

## 🎨 디자인

- **테마**: 파스텔 보라/핑크 그라데이션
- **스타일**: 글라스모피즘
- **배경**: 크림색 (#fdfbf7)
- **액센트**: #a78bfa (보라), #f472b6 (핑크)

---

## ⚠️ 주의사항

1. **API 키**: `.env` 파일에 본인의 OpenAI API 키를 설정하세요.
2. **비용**: Claude CLI는 구독 사용량을 씁니다(분석 1회 약 2분). GPT-4o 백엔드는 API 비용이 발생합니다.
3. **타임아웃**: AI 분석은 최대 120초까지 소요될 수 있습니다.

---

## 📝 라이선스

개인 프로젝트용. 상업적 사용 시 별도 협의 필요.
