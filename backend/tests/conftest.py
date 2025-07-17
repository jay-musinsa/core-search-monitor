import pytest
import asyncio
import os
import sys
from unittest.mock import Mock, patch
from pathlib import Path

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock 모듈들을 미리 설정
sys.modules['app.core.database'] = Mock()
sys.modules['app.core.celery_app'] = Mock()


@pytest.fixture(scope="session")
def event_loop():
    """비동기 테스트를 위한 이벤트 루프"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_database_client():
    """Mock ClickHouse 데이터베이스 클라이언트"""
    mock_client = Mock()
    mock_client.query.return_value = Mock()
    mock_client.query.return_value.result_rows = []
    mock_client.insert.return_value = True
    return mock_client


@pytest.fixture
def mock_redis_client():
    """Mock Redis 클라이언트"""
    with patch('redis.Redis') as mock_redis:
        mock_redis.return_value = Mock()
        yield mock_redis.return_value


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI 클라이언트"""
    with patch('openai.OpenAI') as mock_openai:
        mock_client = Mock()
        mock_openai.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_selenium_driver():
    """Mock Selenium WebDriver"""
    with patch('selenium.webdriver.Chrome') as mock_driver:
        driver_instance = Mock()
        driver_instance.get_screenshot_as_file.return_value = True
        driver_instance.execute_script.return_value = 1000
        mock_driver.return_value = driver_instance
        yield driver_instance


@pytest.fixture
def sample_keyword_data():
    """테스트용 키워드 데이터"""
    return {
        "id": 1,
        "keyword": "테스트 키워드",
        "category": "clothing",
        "priority": 1,
        "is_active": 1
    }


@pytest.fixture
def sample_api_response():
    """테스트용 API 응답 데이터"""
    return {
        "status": "success",
        "data": {
            "products": [
                {
                    "id": "123",
                    "name": "테스트 상품",
                    "brand": "테스트 브랜드",
                    "price": 29900,
                    "image_url": "https://example.com/image.jpg"
                }
            ],
            "total": 1,
            "page": 1
        }
    }


@pytest.fixture
def sample_gpt_response():
    """테스트용 GPT 평가 응답"""
    return {
        "ndcg_score": 0.85,
        "precision": 0.80,
        "recall": 0.75,
        "relevance_score": 0.82,
        "evaluation_text": "검색 결과가 키워드와 관련성이 높음",
        "confidence_score": 0.90
    }


@pytest.fixture
def sample_batch_job():
    """테스트용 배치 작업 데이터"""
    return {
        "batch_id": "test_batch_001",
        "job_type": "daily_assessment",
        "status": "pending",
        "total_keywords": 10,
        "processed_keywords": 0,
        "failed_keywords": 0
    }


@pytest.fixture(autouse=True)
def setup_test_environment():
    """테스트 환경 설정"""
    # 환경 변수 설정
    os.environ['ENVIRONMENT'] = 'test'
    os.environ['OPENAI_API_KEY'] = 'test_key'
    os.environ['REDIS_URL'] = 'redis://localhost:6379/1'
    os.environ['CLICKHOUSE_HOST'] = 'localhost'
    os.environ['CLICKHOUSE_PORT'] = '8123'
    
    yield
    
    # 테스트 후 정리
    test_keys = ['ENVIRONMENT', 'OPENAI_API_KEY', 'REDIS_URL', 'CLICKHOUSE_HOST', 'CLICKHOUSE_PORT']
    for key in test_keys:
        if key in os.environ:
            del os.environ[key]


@pytest.fixture
def celery_app_instance():
    """Celery 앱 인스턴스"""
    return Mock()


@pytest.fixture
def mock_screenshot_path():
    """Mock 스크린샷 파일 경로"""
    return "/tmp/test_screenshot.png"


@pytest.fixture
def mock_file_operations():
    """파일 시스템 작업 Mock"""
    with patch('pathlib.Path.exists') as mock_exists, \
         patch('pathlib.Path.mkdir') as mock_mkdir, \
         patch('pathlib.Path.unlink') as mock_unlink, \
         patch('pathlib.Path.stat') as mock_stat:
        
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 1024
        
        yield {
            'exists': mock_exists,
            'mkdir': mock_mkdir,
            'unlink': mock_unlink,
            'stat': mock_stat
        }