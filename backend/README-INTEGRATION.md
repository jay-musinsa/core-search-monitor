# 통합 테스트 가이드

## 개요

이 문서는 키워드 품질평가 시스템의 통합 테스트 환경 구축 및 실행 방법을 설명합니다.

## 🛠️ 구성 요소

### Docker 기반 통합 테스트 환경

- **ClickHouse**: 분석용 데이터베이스
- **Redis**: 캐시 및 메시지 브로커
- **MinIO**: S3 호환 객체 스토리지
- **Kafka**: 메시지 큐 시스템
- **Selenium Grid**: 웹 브라우저 자동화

### 테스트 구조

```
tests/
├── integration/
│   ├── conftest.py              # 통합 테스트 설정
│   ├── fixtures/
│   │   └── test_data.sql        # 테스트 데이터
│   ├── test_api_endpoints.py    # API 엔드포인트 테스트
│   ├── test_services_integration.py  # 서비스 통합 테스트
│   ├── test_database_integration.py  # 데이터베이스 테스트
│   └── test_external_services.py     # 외부 서비스 테스트
├── test_*.py                    # 단위 테스트
└── conftest.py                  # 단위 테스트 설정
```

## 🚀 빠른 시작

### 1. 의존성 설치

```bash
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### 2. Docker 환경 실행

```bash
# 전체 통합 테스트 실행 (권장)
make docker-test

# 또는 서비스만 시작하고 로컬에서 테스트
make docker-services
make local-integration
```

### 3. 단위 테스트만 실행

```bash
make test-unit
```

## 📋 Make 명령어

### 기본 테스트

```bash
make test                    # 모든 테스트 실행
make test-unit              # 단위 테스트만 실행
make test-integration       # 통합 테스트만 실행
make test-cov               # 커버리지 포함 테스트
```

### Docker 기반 테스트

```bash
make docker-test            # Docker 환경에서 통합 테스트
make docker-build           # Docker 테스트 환경 빌드
make docker-services        # 테스트 서비스만 시작
make docker-clean           # Docker 환경 정리
```

### 특정 테스트

```bash
make test-api               # API 테스트만 실행
make test-services          # 서비스 테스트만 실행
make test-database          # 데이터베이스 테스트만 실행
make test-external          # 외부 서비스 테스트만 실행
```

### 코드 품질

```bash
make lint                   # 코드 린팅
make format                 # 코드 포맷팅
make type-check             # 타입 체킹
make security-check         # 보안 검사
```

### 개발 지원

```bash
make smoke-test             # 빠른 스모크 테스트
make health-check           # 시스템 상태 확인
make docker-logs            # Docker 로그 확인
make clean                  # 임시 파일 정리
```

## 🔧 환경 설정

### 환경 변수

테스트 실행 시 다음 환경 변수가 자동으로 설정됩니다:

```bash
ENVIRONMENT=test
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8124  # Docker 환경
REDIS_URL=redis://localhost:6380/0  # Docker 환경
OPENAI_API_KEY=test_key_for_testing
```

### 커스텀 설정

`pytest.ini` 파일에서 테스트 설정을 커스터마이징할 수 있습니다:

```ini
[tool:pytest]
addopts = -v --tb=short --cov=app --cov-report=html
markers = 
    integration: Integration tests
    slow: Slow running tests
    external: Tests requiring external services
```

## 📊 테스트 마커

테스트는 다음 마커로 분류됩니다:

- `@pytest.mark.integration`: 통합 테스트
- `@pytest.mark.slow`: 느린 테스트
- `@pytest.mark.external`: 외부 서비스 필요
- `@pytest.mark.database`: 데이터베이스 필요
- `@pytest.mark.performance`: 성능 테스트

### 마커별 실행

```bash
pytest -m "integration"     # 통합 테스트만
pytest -m "not slow"        # 빠른 테스트만
pytest -m "database"        # 데이터베이스 테스트만
```

## 🧪 테스트 데이터

### 자동 생성 테스트 데이터

통합 테스트 시작 시 다음 테스트 데이터가 자동으로 생성됩니다:

- **키워드 마스터**: 10개 테스트 키워드
- **품질 평가 결과**: 다양한 시나리오의 평가 데이터
- **배치 작업**: 완료/실행중/실패 상태의 배치 작업
- **시스템 메트릭**: CPU, 메모리, 디스크 사용률 데이터
- **알림 로그**: 다양한 레벨의 알림 이력

### 데이터 정리

각 테스트 후 데이터가 자동으로 정리됩니다:

```python
@pytest.fixture
async def clean_database(test_database):
    yield
    # 테스트 후 데이터 정리
    cleanup_tables = [
        "quality_assessment_daily",
        "keyword_trends", 
        "batch_jobs"
    ]
```

## 🔍 디버깅

### 테스트 실패 시 디버깅

```bash
# 상세한 출력으로 실행
pytest tests/integration/ -v -s

# 실패 시 즉시 중단
pytest tests/integration/ -x

# 특정 테스트만 실행
pytest tests/integration/test_api_endpoints.py::TestQualityDashboardAPI::test_get_quality_dashboard_data_success -v
```

### Docker 로그 확인

```bash
# 모든 서비스 로그
make docker-logs

# 특정 서비스 로그
make logs-clickhouse
make logs-redis
make logs-app
```

### 수동 서비스 테스트

```bash
# ClickHouse 연결 테스트
docker exec -it clickhouse-test clickhouse-client --query "SELECT 1"

# Redis 연결 테스트
docker exec -it redis-test redis-cli ping
```

## 🚀 CI/CD 통합

### GitHub Actions

`.github/workflows/integration-tests.yml`에서 CI/CD 파이프라인이 정의되어 있습니다:

- **단위 테스트**: Python 3.11 환경에서 실행
- **통합 테스트**: Docker 서비스와 함께 실행
- **성능 테스트**: 별도 작업으로 실행
- **보안 검사**: Bandit 및 Safety 도구 사용

### 로컬 CI 시뮬레이션

```bash
# CI와 동일한 검사 실행
make ci-test
```

## 📈 성능 테스트

### 벤치마크 실행

```bash
make benchmark
```

### 성능 메트릭

- **응답 시간**: API 엔드포인트별 응답 시간
- **처리량**: 초당 처리 가능한 키워드 수
- **메모리 사용량**: 대용량 데이터 처리 시 메모리 사용
- **동시성**: 동시 요청 처리 능력

## 🔐 보안 테스트

### 보안 검사 실행

```bash
make security-check
```

### 검사 항목

- **Bandit**: Python 코드 보안 취약점 스캔
- **Safety**: 의존성 라이브러리 보안 취약점 확인
- **의존성 감사**: 알려진 보안 이슈가 있는 패키지 탐지

## 🛟 문제 해결

### 일반적인 문제

#### Docker 서비스 시작 실패

```bash
# Docker 정리 후 재시작
make docker-clean
make docker-services
```

#### 포트 충돌

기본 포트가 사용 중인 경우 `docker-compose.test.yml`에서 포트 변경:

```yaml
ports:
  - "8124:8123"  # ClickHouse
  - "6380:6379"  # Redis
```

#### 테스트 데이터 초기화 실패

```bash
# 수동으로 데이터베이스 초기화
python database/init_db.py
```

### 성능 이슈

#### 테스트 실행 속도 개선

```bash
# 병렬 테스트 실행
make test-parallel

# 빠른 테스트만 실행
make test-fast
```

#### 메모리 사용량 최적화

- Docker 컨테이너 메모리 제한 설정
- 테스트 데이터 크기 조정
- 배치 크기 최적화

## 📚 추가 리소스

- [pytest 공식 문서](https://docs.pytest.org/)
- [Docker Compose 가이드](https://docs.docker.com/compose/)
- [ClickHouse 테스트 가이드](https://clickhouse.com/docs/en/development/tests/)
- [FastAPI 테스트 가이드](https://fastapi.tiangolo.com/tutorial/testing/)

## 🤝 기여 가이드

새로운 테스트 추가 시:

1. 적절한 마커 추가
2. 테스트 데이터 정리 로직 포함
3. 문서 업데이트
4. CI/CD 파이프라인 확인

### 테스트 작성 가이드라인

- **AAA 패턴**: Arrange, Act, Assert 구조 사용
- **독립성**: 각 테스트는 독립적으로 실행 가능
- **반복성**: 동일한 결과를 보장
- **명확성**: 테스트 목적과 기대 결과를 명확히 명시