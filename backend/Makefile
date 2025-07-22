# Makefile for Backend Integration Testing

.PHONY: help install test test-unit test-integration test-all docker-test docker-build docker-clean lint format type-check security-check clean dev-setup dev-start dev-stop init-db

# 기본 타겟
help:
	@echo "Available commands:"
	@echo "  install           - Install dependencies"
	@echo "  dev-setup         - Setup development environment"
	@echo "  dev-start         - Start development services"
	@echo "  dev-stop          - Stop development services"
	@echo "  init-db           - Initialize ClickHouse database"
	@echo "  test             - Run all tests"
	@echo "  test-unit        - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-performance - Run performance tests"
	@echo "  docker-test      - Run tests in Docker environment"
	@echo "  docker-build     - Build Docker test environment"
	@echo "  docker-clean     - Clean Docker test environment"
	@echo "  lint             - Run code linting"
	@echo "  format           - Format code"
	@echo "  type-check       - Run type checking"
	@echo "  security-check   - Run security checks"
	@echo "  clean            - Clean temporary files"

# 의존성 설치
install:
	pip install -r requirements.txt
	pip install -r requirements-test.txt

# 개발환경 설정
dev-setup: install
	@echo "Setting up development environment..."
	@cd .. && docker-compose -f docker-compose.dev.yml up -d
	@sleep 10
	@echo "Initializing ClickHouse database..."
	@python database/init_db.py
	@echo "Development environment setup complete!"

# 개발 서비스 시작
dev-start:
	@echo "Starting development services..."
	@cd .. && docker-compose -f docker-compose.dev.yml up -d

# 개발 서비스 종료
dev-stop:
	@echo "Stopping development services..."
	@cd .. && docker-compose -f docker-compose.dev.yml down

# ClickHouse 데이터베이스 초기화
init-db:
	@echo "Initializing ClickHouse database..."
	@python database/init_db.py

# 단위 테스트 실행
test-unit:
	pytest tests/test_*.py -m "not integration" -v

# 통합 테스트 실행 (로컬)
test-integration:
	pytest tests/integration/ -v

# 성능 테스트 실행
test-performance:
	pytest tests/integration/ -m "performance" -v

# 모든 테스트 실행
test:
	pytest tests/ -v

# 테스트 커버리지 포함 실행
test-cov:
	pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# Docker 환경에서 통합 테스트 실행
docker-test: docker-build
	@echo "Starting Docker test environment..."
	docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
	@echo "Cleaning up Docker test environment..."
	docker-compose -f docker-compose.test.yml down -v

# Docker 테스트 환경만 빌드
docker-build:
	@echo "Building Docker test environment..."
	docker-compose -f docker-compose.test.yml build

# Docker 테스트 서비스만 시작 (개발용)
docker-services:
	@echo "Starting test services only..."
	docker-compose -f docker-compose.test.yml up -d clickhouse-test redis-test minio-test kafka-test selenium-hub selenium-chrome
	@echo "Waiting for services to be ready..."
	sleep 30
	@echo "Services are ready!"

# Docker 테스트 서비스 중지
docker-services-stop:
	docker-compose -f docker-compose.test.yml stop

# Docker 환경 정리
docker-clean:
	docker-compose -f docker-compose.test.yml down -v --remove-orphans
	docker system prune -f

# 특정 테스트 실행
test-api:
	pytest tests/integration/test_api_endpoints.py -v

test-services:
	pytest tests/integration/test_services_integration.py -v

test-database:
	pytest tests/integration/test_database_integration.py -v

test-external:
	pytest tests/integration/test_external_services.py -v

# 코드 품질 검사
lint:
	flake8 app/ tests/ --max-line-length=120 --ignore=E203,E501,W503
	black --check app/ tests/
	isort --check-only app/ tests/

# 코드 포맷팅
format:
	black app/ tests/
	isort app/ tests/

# 타입 체킹
type-check:
	mypy app/ --ignore-missing-imports

# 보안 검사
security-check:
	bandit -r app/ -f json -o security-report.json
	safety check

# 빠른 스모크 테스트 (Docker 없이)
smoke-test:
	pytest tests/test_gpt_service.py::TestGPTService::test_gpt_service_initialization -v
	pytest tests/integration/test_api_endpoints.py::TestQualityDashboardAPI::test_health_check_success -v

# 개발 환경 설정
dev-setup: install
	@echo "Setting up development environment..."
	pre-commit install || echo "pre-commit not available"
	@echo "Development environment ready!"

# 테스트 데이터베이스 초기화
init-test-db:
	python -c "from tests.integration.conftest import *; import asyncio; asyncio.run(init_test_database())"

# 테스트 리포트 생성
test-report:
	pytest tests/ --html=reports/test-report.html --self-contained-html --json-report --json-report-file=reports/test-report.json

# CI/CD 테스트 (모든 검사 포함)
ci-test: lint type-check security-check test-cov
	@echo "All CI checks completed successfully!"

# 로컬 통합 테스트 (Docker 서비스만 사용)
local-integration: docker-services
	@echo "Running integration tests with Docker services..."
	sleep 10
	CLICKHOUSE_HOST=localhost \
	CLICKHOUSE_PORT=8124 \
	REDIS_URL=redis://localhost:6380/0 \
	pytest tests/integration/ -v || true
	$(MAKE) docker-services-stop

# 성능 벤치마크
benchmark:
	pytest tests/integration/ -m "performance" --benchmark-only --benchmark-json=reports/benchmark.json

# 테스트 환경 변수 확인
check-env:
	@echo "Checking test environment variables..."
	@echo "CLICKHOUSE_HOST: $(CLICKHOUSE_HOST)"
	@echo "CLICKHOUSE_PORT: $(CLICKHOUSE_PORT)"
	@echo "REDIS_URL: $(REDIS_URL)"
	@echo "ENVIRONMENT: $(ENVIRONMENT)"

# 임시 파일 정리
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf reports/
	rm -rf .coverage

# 전체 정리 (Docker 포함)
clean-all: clean docker-clean
	docker volume prune -f

# 병렬 테스트 실행
test-parallel:
	pytest tests/ -n auto -v

# 특정 마커로 테스트 실행
test-slow:
	pytest tests/ -m "slow" -v

test-fast:
	pytest tests/ -m "not slow" -v

# 테스트 실패 시 디버그 모드
test-debug:
	pytest tests/ --pdb --pdbcls=IPython.terminal.debugger:Pdb -v

# 커버리지 리포트만 생성
coverage-report:
	coverage html
	coverage report

# 통합 테스트 헬스체크
health-check:
	@echo "Checking Docker services health..."
	docker-compose -f docker-compose.test.yml ps
	@echo "Checking database connectivity..."
	python -c "from app.core.database import get_database_client; client = get_database_client(); print('DB connected:', client.query('SELECT 1').result_rows[0][0] == 1)" || echo "Database connection failed"

# Docker 로그 확인
docker-logs:
	docker-compose -f docker-compose.test.yml logs -f

# 특정 서비스 로그 확인
logs-clickhouse:
	docker-compose -f docker-compose.test.yml logs -f clickhouse-test

logs-redis:
	docker-compose -f docker-compose.test.yml logs -f redis-test

logs-app:
	docker-compose -f docker-compose.test.yml logs -f app-test