# 무신사 검색 성능 모니터링 시스템

AI 기반 실시간 검색 품질 모니터링 시스템

## 🚀 빠른 시작

### 1. 의존성 설치
```bash
make install
```

### 2. Docker 서비스 시작
```bash
make dev-up
```

### 3. 백엔드 서버 실행
```bash
make backend
```

### 4. 프론트엔드 서버 실행 (새 터미널)
```bash
make frontend
```

## 📍 접속 URL

- 프론트엔드: http://localhost:3000
- 백엔드 API: http://localhost:8000
- API 문서: http://localhost:8000/docs
- Redis: localhost:6379
- Kafka: localhost:9092

## 🛠 개발 명령어

- `make test` - 테스트 실행
- `make dev-down` - Docker 서비스 중지
- `make clean` - 캐시 정리
- `make help` - 도움말 표시

## 📚 프로젝트 구조

```
musinsa-search-monitor/
├── backend/          # Python FastAPI 백엔드
├── frontend/         # React 프론트엔드
├── docker-compose.dev.yml
├── Makefile
└── README.md
```
