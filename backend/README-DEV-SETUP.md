# 개발환경 설정 가이드

## 🚀 빠른 시작

### 1. 개발 서비스 시작
```bash
cd backend
make dev-start
```

### 2. 데이터베이스 초기화
```bash
cd backend
source venv/bin/activate
python database/init_db.py
```

### 3. 백엔드 서버 시작
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

## 📋 상세 설정 가이드

### 필수 조건
- Docker & Docker Compose
- Python 3.9+
- Node.js 18+ (프론트엔드용)

### 1단계: 의존성 설치
```bash
cd backend

# 가상환경 활성화
source venv/bin/activate

# Python 패키지 설치
pip install -r requirements.txt
```

### 2단계: 인프라 서비스 시작
```bash
# 루트 디렉토리에서 실행
docker-compose -f docker-compose.dev.yml up -d
```

이 명령어는 다음 서비스들을 시작합니다:
- **ClickHouse** (포트 8123, 9000) - 메인 데이터베이스
- **Redis** (포트 6379) - 캐시 및 세션 스토어
- **Kafka + Zookeeper** (포트 9092, 2181) - 메시지 큐
- **Kafka UI** (포트 8080) - Kafka 관리 웹 인터페이스
- **Redis Insight** (포트 8001) - Redis 관리 웹 인터페이스

### 3단계: ClickHouse 데이터베이스 초기화
```bash
cd backend
source venv/bin/activate
python database/init_db.py
```

### 4단계: 백엔드 서버 시작
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

## 🔧 Makefile 명령어

```bash
# 도움말 보기
make help

# 개발환경 전체 설정 (권장)
make dev-setup

# 개발 서비스만 시작
make dev-start

# 개발 서비스 종료
make dev-stop

# ClickHouse 데이터베이스만 초기화
make init-db

# 테스트 실행
make test

# 코드 품질 검사
make lint
```

## 🌐 서비스 접속 정보

### 백엔드 API
- URL: http://localhost:8000
- 헬스체크: http://localhost:8000/health
- API 문서: http://localhost:8000/docs

### 관리 도구
- **Kafka UI**: http://localhost:8080
- **Redis Insight**: http://localhost:8001
- **ClickHouse**: localhost:8123 (HTTP), localhost:9000 (Native)

### 프론트엔드 (별도 시작 필요)
- URL: http://localhost:3000

## 🗄️ 데이터베이스 구조

초기화 후 다음 테이블들이 생성됩니다:

1. **keyword_master** - 키워드 마스터 테이블
2. **quality_assessment_daily** - 일일 품질평가 결과
3. **keyword_trends** - 키워드별 추이 분석
4. **batch_jobs** - 배치 작업 관리
5. **system_metrics** - 시스템 성능 모니터링

### 샘플 데이터
초기화 시 다음 샘플 키워드가 삽입됩니다:
- 원피스, 청바지, 운동화, 백팩, 시계

## 🔍 트러블슈팅

### ClickHouse 연결 오류
```bash
# ClickHouse 서비스 상태 확인
docker ps | grep clickhouse

# ClickHouse 로그 확인
docker logs musinsa-search-monitor-clickhouse-1

# 수동 연결 테스트
curl http://localhost:8123/ping
```

### Redis 연결 오류
```bash
# Redis 서비스 상태 확인
docker ps | grep redis

# Redis 연결 테스트
docker exec -it musinsa-search-monitor-redis-1 redis-cli ping
```

### 포트 충돌
기본 포트가 이미 사용 중인 경우:
1. `docker-compose.dev.yml`에서 포트 변경
2. `backend/config.py`에서 해당 설정 업데이트

### 권한 오류
```bash
# Docker 권한 확인
sudo usermod -aG docker $USER

# 로그아웃 후 다시 로그인 필요
```

## 🧪 테스트

### 단위 테스트
```bash
cd backend
make test-unit
```

### 통합 테스트
```bash
cd backend
make test-integration
```

### 전체 테스트 (Docker 환경)
```bash
cd backend
make docker-test
```

## 📝 개발 팁

1. **핫 리로드**: `--reload` 옵션으로 코드 변경 시 자동 재시작
2. **API 문서**: http://localhost:8000/docs 에서 대화형 API 문서 확인
3. **로그 모니터링**: `docker-compose logs -f [service-name]`로 실시간 로그 확인
4. **데이터베이스 재초기화**: 필요시 `python database/init_db.py` 재실행

## 🚫 주의사항

- 개발환경 설정이므로 운영환경에서 사용하지 마세요
- `.env` 파일에 민감한 정보를 저장하지 마세요
- Docker 볼륨 데이터는 `docker-compose down -v`로 삭제 가능합니다

## 📞 지원

문제가 발생하면:
1. 이 문서의 트러블슈팅 섹션 확인
2. 로그 파일 검토
3. 개발팀에 문의 