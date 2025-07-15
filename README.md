# 무신사 검색 품질 모니터링 시스템

AI 기반 실시간 검색 품질 모니터링 및 평가 시스템

## 📖 프로젝트 개요

무신사 검색 품질 모니터링 시스템은 무신사 쇼핑몰의 검색 결과를 실시간으로 모니터링하고, GPT-4o를 활용하여 검색 품질을 자동으로 평가하는 시스템입니다. 검색 키워드를 입력하면 자동으로 무신사 사이트를 크롤링하고, 스크린샷을 생성한 후 AI가 검색 결과의 품질을 평가합니다.

## 🎯 주요 기능

### 1. 실시간 검색 모니터링
- 키워드 입력을 통한 무신사 검색 결과 자동 크롤링
- Selenium을 활용한 실제 브라우저 환경에서의 스크린샷 생성
- WebSocket을 통한 실시간 진행 상황 표시

### 2. AI 기반 검색 품질 평가
- **GPT-4o Vision API**를 활용한 검색 결과 스크린샷 분석
- 3가지 핵심 메트릭 자동 계산:
  - **NDCG@10**: 상위 10개 결과의 관련성 순위 평가 (0.0-1.0)
  - **Precision**: 관련성 있는 결과의 비율 (0.0-1.0)
  - **Recall**: 전체 관련 아이템 중 검색된 비율 (0.0-1.0)
- 각 메트릭별 상세한 평가 이유 제공

### 3. 실시간 프로그레스 표시
- 4단계 진행 상황 실시간 표시:
  1. **25%** - 무신사 검색 진행중
  2. **50%** - 스크린샷 생성 완료
  3. **75%** - AI 평가 진행중
  4. **100%** - 평가 완료

### 4. 직관적인 웹 인터페이스
- React 기반 반응형 웹 UI
- 실시간 메트릭 표시 및 평가 이유 제공
- 검색 결과 스크린샷 미리보기
- 키워드별 평가 히스토리 관리

## 🛠 기술 스택

### Backend
- **FastAPI**: 고성능 비동기 웹 프레임워크
- **Python 3.8+**: 메인 개발 언어
- **Selenium**: 웹 크롤링 및 스크린샷 생성
- **OpenAI GPT-4o**: AI 기반 검색 품질 평가
- **WebSocket**: 실시간 통신
- **ThreadPoolExecutor**: 비동기 작업 처리

### Frontend
- **React 18**: 사용자 인터페이스
- **JavaScript (ES6+)**: 클라이언트 사이드 로직
- **WebSocket**: 실시간 상태 업데이트
- **Axios**: HTTP 클라이언트

### Infrastructure
- **Docker**: 컨테이너화
- **Redis**: 캐싱 및 세션 관리
- **Kafka**: 메시지 큐잉
- **ClickHouse**: 분석용 데이터베이스

## 📁 프로젝트 구조

```
musinsa-search-monitor/
├── backend/                    # Python FastAPI 백엔드
│   ├── app/
│   │   ├── api/               # API 라우터
│   │   │   └── metrics.py     # 메트릭 관련 API
│   │   ├── core/              # 핵심 비즈니스 로직
│   │   │   ├── crawler.py     # 무신사 크롤링
│   │   │   ├── gpt.py         # GPT 평가 로직
│   │   │   ├── metrics.py     # 메트릭 관리
│   │   │   └── consumer.py    # 메시지 처리
│   │   ├── models/            # 데이터 모델
│   │   ├── screenshot/        # 스크린샷 저장소
│   │   └── main.py           # 애플리케이션 엔트리포인트
│   ├── config.py             # 설정 관리
│   ├── requirements.txt      # Python 의존성
│   └── infrastructure/       # 인프라 설정
├── frontend/                 # React 프론트엔드
│   ├── src/
│   │   ├── components/       # React 컴포넌트
│   │   │   └── MetricsTable.js
│   │   ├── services/         # API 서비스
│   │   │   └── metricsApi.js
│   │   ├── App.js           # 메인 앱 컴포넌트
│   │   └── index.js         # 앱 엔트리포인트
│   └── package.json         # Node.js 의존성
├── docker-compose.dev.yml   # 개발 환경 Docker 설정
├── Makefile                 # 빌드 자동화
└── README.md               # 프로젝트 문서
```

## 🚀 빠른 시작

### 1. 환경 설정
```bash
# 저장소 클론
git clone <repository-url>
cd musinsa-search-monitor

# 의존성 설치
make install
```

### 2. 환경 변수 설정
```bash
# backend/config.py에서 OpenAI API 키 설정
export OPENAI_API_KEY="your-openai-api-key"
```

### 3. Docker 서비스 시작
```bash
make dev-up
```

### 4. 백엔드 서버 실행
```bash
make backend
```

### 5. 프론트엔드 서버 실행 (새 터미널)
```bash
make frontend
```

## 📍 접속 URL

- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **Redis**: localhost:6379
- **Kafka**: localhost:9092

## 🎮 사용 방법

1. **웹 인터페이스 접속**: http://localhost:3000
2. **키워드 입력**: 검색하고 싶은 패션 아이템 키워드 입력 (예: "반팔티", "청바지")
3. **실시간 모니터링**: 4단계 프로그레스 바를 통해 진행 상황 확인
4. **결과 확인**: AI 평가 결과 및 상세한 분석 이유 확인
5. **스크린샷 확인**: 실제 검색 결과 스크린샷 미리보기

## 🔧 개발 명령어

```bash
# 테스트 실행
make test

# Docker 서비스 중지
make dev-down

# 캐시 정리
make clean

# 도움말 표시
make help
```

## 🏗 시스템 아키텍처

### 데이터 플로우
1. **사용자 입력** → 키워드 입력 및 검색 요청
2. **크롤링** → Selenium을 통한 무신사 사이트 검색
3. **스크린샷** → 검색 결과 페이지 자동 캡처
4. **AI 평가** → GPT-4o를 통한 검색 품질 분석
5. **결과 표시** → 실시간 메트릭 및 평가 이유 제공

### 핵심 컴포넌트
- **WebSocket Manager**: 실시간 상태 업데이트
- **Crawler Engine**: 무신사 사이트 자동 크롤링
- **GPT Evaluator**: AI 기반 검색 품질 평가
- **Metrics Manager**: 평가 결과 관리 및 저장

## 📊 평가 메트릭

### NDCG@10 (Normalized Discounted Cumulative Gain)
- 상위 10개 검색 결과의 관련성과 순위를 종합 평가
- 높은 관련성의 결과가 상위에 위치할수록 높은 점수

### Precision (정밀도)
- 전체 검색 결과 중 관련성 있는 결과의 비율
- 검색 결과의 정확성을 측정

### Recall (재현율)
- 전체 관련 아이템 중 실제로 검색된 아이템의 비율
- 검색 결과의 완성도를 측정

## 🔐 보안 및 설정

### API 키 관리
- OpenAI API 키는 환경 변수로 관리
- `backend/README_API_KEY.md` 참조

### CORS 설정
- 프론트엔드(localhost:3000)에서의 API 접근 허용
- 프로덕션 환경에서는 도메인 제한 필요

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 문의

프로젝트 관련 문의사항이 있으시면 이슈를 생성해주세요.
