import pytest
import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator
import httpx
import docker
import time
from testcontainers.clickhouse import ClickHouseContainer
from testcontainers.redis import RedisContainer

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.database import get_database_client
from app.services.batch_optimizer import BatchOptimizer
from app.services.trend_analyzer import TrendAnalyzer
from app.services.image_storage import ImageStorage
from app.services.notification_service import NotificationService


@pytest.fixture(scope="session")
def event_loop():
    """세션 범위의 이벤트 루프"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def docker_client():
    """Docker 클라이언트"""
    return docker.from_env()


@pytest.fixture(scope="session")
def clickhouse_container():
    """ClickHouse 테스트 컨테이너"""
    with ClickHouseContainer("clickhouse/clickhouse-server:23.3") as clickhouse:
        # 스키마 초기화 대기
        time.sleep(10)
        yield clickhouse


@pytest.fixture(scope="session")
def redis_container():
    """Redis 테스트 컨테이너"""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


@pytest.fixture(scope="session")
def test_database(clickhouse_container):
    """테스트 데이터베이스 설정"""
    # 환경 변수 설정
    os.environ["CLICKHOUSE_HOST"] = clickhouse_container.get_container_host_ip()
    os.environ["CLICKHOUSE_PORT"] = str(clickhouse_container.get_exposed_port(8123))
    os.environ["CLICKHOUSE_USER"] = "default"
    os.environ["CLICKHOUSE_PASSWORD"] = ""
    
    # 데이터베이스 클라이언트 생성
    db_client = get_database_client()
    
    # 스키마 생성
    schema_path = Path(__file__).parent.parent.parent / "database" / "schema.sql"
    if schema_path.exists():
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        
        # SQL 문을 개별적으로 실행
        statements = [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]
        for statement in statements:
            if statement and not statement.startswith("--"):
                try:
                    db_client.query(statement)
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        print(f"Schema creation warning: {e}")
    
    # 테스트 데이터 삽입
    test_data_path = Path(__file__).parent / "fixtures" / "test_data.sql"
    if test_data_path.exists():
        with open(test_data_path, "r", encoding="utf-8") as f:
            test_data_sql = f.read()
        
        statements = [stmt.strip() for stmt in test_data_sql.split(";") if stmt.strip()]
        for statement in statements:
            if statement and not statement.startswith("--"):
                try:
                    db_client.query(statement)
                except Exception as e:
                    print(f"Test data insertion warning: {e}")
    
    yield db_client
    
    # 정리
    try:
        db_client.query("DROP DATABASE IF EXISTS test_db")
    except:
        pass


@pytest.fixture(scope="session")
def test_redis(redis_container):
    """테스트 Redis 설정"""
    import redis
    
    # 환경 변수 설정
    redis_host = redis_container.get_container_host_ip()
    redis_port = redis_container.get_exposed_port(6379)
    os.environ["REDIS_URL"] = f"redis://{redis_host}:{redis_port}/0"
    
    # Redis 클라이언트 생성
    redis_client = redis.Redis(host=redis_host, port=redis_port, db=0)
    
    # 연결 테스트
    redis_client.ping()
    
    yield redis_client
    
    # 정리
    redis_client.flushall()


@pytest.fixture(scope="session") 
async def test_app():
    """테스트 FastAPI 애플리케이션"""
    from app.main import app
    
    # 테스트 환경 설정
    os.environ["ENVIRONMENT"] = "test"
    
    yield app


@pytest.fixture(scope="session")
async def test_client(test_app):
    """테스트 HTTP 클라이언트"""
    async with httpx.AsyncClient(
        app=test_app,
        base_url="http://testserver",
        timeout=30.0
    ) as client:
        yield client


@pytest.fixture
def batch_optimizer_service(test_database, test_redis):
    """배치 최적화 서비스 테스트 인스턴스"""
    return BatchOptimizer()


@pytest.fixture
def trend_analyzer_service(test_database, test_redis):
    """트렌드 분석 서비스 테스트 인스턴스"""
    return TrendAnalyzer()


@pytest.fixture
def image_storage_service(test_database, test_redis):
    """이미지 저장소 서비스 테스트 인스턴스"""
    config = {
        "local_storage_path": "/tmp/test_screenshots",
        "use_s3": False,
        "enable_compression": True,
        "enable_thumbnail": True
    }
    return ImageStorage(config)


@pytest.fixture
def notification_service_instance(test_database, test_redis):
    """알림 서비스 테스트 인스턴스"""
    config = {
        "email": {
            "smtp_server": "localhost",
            "smtp_port": 1025,  # 테스트용 SMTP 포트
            "username": "test@example.com",
            "password": "testpass",
            "from_email": "test@example.com"
        },
        "slack": {
            "webhook_url": "http://localhost:3000/test-webhook"
        },
        "webhook": {
            "default_url": "http://localhost:3001/test-webhook"
        },
        "monitoring": {
            "check_interval": 10,  # 테스트용 짧은 간격
            "batch_size": 5
        }
    }
    return NotificationService(config)


@pytest.fixture
def sample_keyword_data():
    """샘플 키워드 데이터"""
    return {
        "id": 1,
        "keyword": "테스트키워드1",
        "category": "clothing",
        "priority": 1,
        "is_active": 1
    }


@pytest.fixture
def sample_quality_data():
    """샘플 품질 데이터"""
    return {
        "keyword_id": 1,
        "platform": "musinsa",
        "ndcg_score": 0.85,
        "precision": 0.80,
        "recall": 0.75,
        "relevance_score": 0.82,
        "confidence_score": 0.90,
        "evaluation_text": "검색 결과가 키워드와 관련성이 높음",
        "screenshot_path": "/screenshots/test_1.png",
        "processing_time": 3.5,
        "api_response_time": 1.2,
        "api_total_results": 50
    }


@pytest.fixture
def sample_batch_request():
    """샘플 배치 요청 데이터"""
    return {
        "platforms": ["musinsa"],
        "keywordCount": 10,
        "targetDate": "2024-01-01",
        "batchSize": 5,
        "maxWorkers": 2
    }


@pytest.fixture(autouse=True)
def setup_test_environment():
    """테스트 환경 자동 설정"""
    # 테스트 환경 변수 설정
    test_env_vars = {
        "ENVIRONMENT": "test",
        "LOG_LEVEL": "DEBUG",
        "OPENAI_API_KEY": "test_key_for_testing",
        "AWS_ACCESS_KEY_ID": "test_access_key",
        "AWS_SECRET_ACCESS_KEY": "test_secret_key",
        "AWS_S3_BUCKET": "test-bucket",
        "SMTP_SERVER": "localhost",
        "SMTP_PORT": "1025",
        "SLACK_WEBHOOK_URL": "http://localhost:3000/test-webhook"
    }
    
    # 환경 변수 설정
    original_env = {}
    for key, value in test_env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # 환경 변수 복원
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
async def clean_database(test_database):
    """데이터베이스 정리"""
    yield
    
    # 테스트 후 데이터 정리
    cleanup_tables = [
        "quality_assessment_daily",
        "keyword_trends", 
        "batch_jobs",
        "system_metrics",
        "notification_logs"
    ]
    
    for table in cleanup_tables:
        try:
            test_database.query(f"TRUNCATE TABLE {table}")
        except Exception as e:
            print(f"Warning: Could not truncate {table}: {e}")


@pytest.fixture
def mock_external_services(monkeypatch):
    """외부 서비스 모킹"""
    import requests
    from unittest.mock import Mock, patch
    
    # OpenAI API 모킹
    mock_openai_response = {
        "choices": [{
            "message": {
                "content": '{"ndcg_score": 0.85, "precision": 0.80, "recall": 0.75, "relevance_score": 0.82}'
            }
        }]
    }
    
    with patch('openai.OpenAI') as mock_openai:
        mock_openai.return_value.chat.completions.create.return_value = Mock(**mock_openai_response)
        
        # Selenium WebDriver 모킹
        with patch('selenium.webdriver.Chrome') as mock_driver:
            mock_driver_instance = Mock()
            mock_driver_instance.get_screenshot_as_file.return_value = True
            mock_driver_instance.execute_script.return_value = 1000
            mock_driver.return_value = mock_driver_instance
            
            # HTTP 요청 모킹
            with patch('requests.post') as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = {"success": True}
                
                yield {
                    'openai': mock_openai,
                    'selenium': mock_driver,
                    'requests': mock_post
                }