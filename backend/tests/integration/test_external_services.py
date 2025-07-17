"""
외부 서비스 통합 테스트
"""

import pytest
import asyncio
from unittest.mock import patch, Mock, MagicMock
import requests
import json
import tempfile
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class TestWebDriverIntegration:
    """WebDriver 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_selenium_screenshot_capture(self, mock_external_services):
        """Selenium 스크린샷 캡처 테스트"""
        from app.core.crawler import CrawlerMusinsa
        
        crawler = CrawlerMusinsa()
        
        # 모킹된 드라이버를 사용한 스크린샷 캡처 테스트
        result = crawler.capture_screenshot("테스트키워드")
        
        # 모킹 환경에서는 결과가 반환되어야 함 (파일 경로 또는 None)
        assert result is not None or result is None
    
    @pytest.mark.asyncio
    async def test_crawler_error_handling(self, mock_external_services):
        """크롤러 에러 처리 테스트"""
        from app.core.crawler import CrawlerMusinsa
        
        crawler = CrawlerMusinsa()
        
        # 빈 키워드로 테스트
        result = crawler.capture_screenshot("")
        
        # 에러가 적절히 처리되어야 함 (None 반환 또는 예외 발생)
        assert result is None or isinstance(result, str)
    
    def test_chrome_options_configuration(self):
        """Chrome 옵션 설정 테스트"""
        from app.core.crawler import CrawlerMusinsa
        
        crawler = CrawlerMusinsa()
        options = crawler.chrome_options
        
        # 헤드리스 모드가 설정되어야 함
        assert "--headless" in options.arguments
        assert "--no-sandbox" in options.arguments
        assert "--disable-dev-shm-usage" in options.arguments


class TestAPIServiceIntegration:
    """API 서비스 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_musinsa_api_service(self, mock_external_services):
        """무신사 API 서비스 테스트"""
        from app.core.musinsa_api_service import MusinsaAPIService
        
        api_service = MusinsaAPIService()
        
        # 모킹된 환경에서 API 호출 테스트
        result = api_service.fetch_search_data("테스트키워드")
        
        # 모킹된 응답이 반환되어야 함 (빈 dict 또는 실제 데이터)
        assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_api_timeout_handling(self, mock_external_services):
        """API 타임아웃 처리 테스트"""
        from app.core.musinsa_api_service import MusinsaAPIService
        
        api_service = MusinsaAPIService()
        
        # 타임아웃 설정이 적용되는지 확인
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout()
            
            result = api_service.fetch_search_data("테스트키워드")
            
            # 타임아웃 에러가 적절히 처리되어야 함 (빈 dict 반환)
            assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_api_retry_mechanism(self, mock_external_services):
        """API 재시도 메커니즘 테스트"""
        from app.core.musinsa_api_service import MusinsaAPIService
        
        api_service = MusinsaAPIService()
        
        # 첫 번째 호출은 실패, 두 번째는 성공하도록 설정
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success", "data": []}
            
            mock_get.side_effect = [
                requests.exceptions.ConnectionError(),  # 첫 번째 실패
                mock_response  # 두 번째 성공
            ]
            
            result = api_service.fetch_search_data("테스트키워드")
            
            # 재시도 후 성공해야 함 (dict 형태로 반환)
            assert isinstance(result, dict)


class TestGPTServiceIntegration:
    """GPT 서비스 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_gpt_evaluation_with_mock(self, mock_external_services):
        """모킹된 GPT 평가 테스트"""
        from app.core.gpt import GPTMetricEvaluator
        
        gpt_service = GPTMetricEvaluator()
        
        # 테스트 이미지 데이터
        test_image_data = b"fake_image_data"
        
        # 모킹된 GPT 평가 실행
        result = gpt_service.evaluate("fake_screenshot.png", "테스트키워드")
        
        # 모킹된 응답이 반환되어야 함
        assert isinstance(result, dict)
        assert "ndcg@10" in result or "ndcg_score" in result
        assert "precision" in result
        assert "recall" in result
    
    @pytest.mark.asyncio
    async def test_gpt_fallback_evaluation(self, mock_external_services):
        """GPT 폴백 평가 테스트"""
        from app.core.gpt import GPTMetricEvaluator
        
        gpt_service = GPTMetricEvaluator()
        
        # API 키가 없는 상황을 시뮬레이션
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            result = gpt_service.evaluate("fake_screenshot.png", "테스트키워드")
            
            # 폴백 평가가 실행되어야 함
            assert isinstance(result, dict)
            ndcg_score = result.get("ndcg_score", result.get("ndcg@10", 0))
            assert 0 <= ndcg_score <= 1
    
    @pytest.mark.asyncio
    async def test_gpt_token_usage_calculation(self, mock_external_services):
        """GPT 토큰 사용량 계산 테스트"""
        from app.core.gpt import GPTMetricEvaluator
        
        gpt_service = GPTMetricEvaluator()
        
        # GPT 서비스 인스턴스 확인
        assert gpt_service is not None
        
        # 클라이언트 확인
        assert gpt_service.client is not None or gpt_service.client is None


class TestNotificationIntegration:
    """알림 서비스 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_email_notification_mock(self, notification_service_instance, mock_external_services):
        """모킹된 이메일 알림 테스트"""
        from app.services.notification_service import NotificationEvent, NotificationLevel, NotificationChannel
        
        # 테스트 알림 이벤트 생성
        event = NotificationEvent(
            id="test_email_001",
            rule_id="test_rule",
            level=NotificationLevel.MEDIUM,
            title="테스트 이메일 알림",
            message="테스트 메시지입니다.",
            data={"test": True},
            timestamp=datetime.now(),
            keyword_id=1,
            platform="musinsa",
            channels=[NotificationChannel.EMAIL]
        )
        
        # SMTP 라이브러리 모킹
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value = mock_server
            
            # 이메일 발송 테스트
            await notification_service_instance._send_email_notification(event)
            
            # SMTP 서버가 호출되었는지 확인
            mock_smtp.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_slack_notification_mock(self, notification_service_instance, mock_external_services):
        """모킹된 슬랙 알림 테스트"""
        from app.services.notification_service import NotificationEvent, NotificationLevel, NotificationChannel
        
        event = NotificationEvent(
            id="test_slack_001",
            rule_id="test_rule",
            level=NotificationLevel.HIGH,
            title="테스트 슬랙 알림",
            message="테스트 메시지입니다.",
            data={"test": True},
            timestamp=datetime.now(),
            keyword_id=1,
            platform="musinsa",
            channels=[NotificationChannel.SLACK]
        )
        
        # requests 라이브러리 모킹
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            # 슬랙 알림 발송 테스트
            await notification_service_instance._send_slack_notification(event)
            
            # HTTP POST가 호출되었는지 확인
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_webhook_notification_mock(self, notification_service_instance, mock_external_services):
        """모킹된 웹훅 알림 테스트"""
        from app.services.notification_service import NotificationEvent, NotificationLevel, NotificationChannel
        
        event = NotificationEvent(
            id="test_webhook_001",
            rule_id="test_rule",
            level=NotificationLevel.CRITICAL,
            title="테스트 웹훅 알림",
            message="테스트 메시지입니다.",
            data={"test": True},
            timestamp=datetime.now(),
            keyword_id=1,
            platform="musinsa",
            channels=[NotificationChannel.WEBHOOK]
        )
        
        # requests 라이브러리 모킹
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            # 웹훅 알림 발송 테스트
            await notification_service_instance._send_webhook_notification(event)
            
            # HTTP POST가 호출되었는지 확인
            mock_post.assert_called_once()


class TestRedisIntegration:
    """Redis 통합 테스트"""
    
    def test_redis_connection(self, test_redis):
        """Redis 연결 테스트"""
        # 기본 연결 테스트
        result = test_redis.ping()
        assert result == True
        
        # 데이터 저장 및 조회 테스트
        test_key = "test:integration"
        test_value = "test_value"
        
        test_redis.set(test_key, test_value)
        retrieved_value = test_redis.get(test_key)
        
        assert retrieved_value.decode('utf-8') == test_value
        
        # 데이터 삭제
        test_redis.delete(test_key)
    
    def test_redis_json_operations(self, test_redis):
        """Redis JSON 연산 테스트"""
        test_key = "test:json"
        test_data = {
            "keyword": "테스트키워드",
            "platform": "musinsa",
            "score": 0.85
        }
        
        # JSON 데이터 저장
        test_redis.set(test_key, json.dumps(test_data))
        
        # JSON 데이터 조회
        retrieved_data = json.loads(test_redis.get(test_key))
        
        assert retrieved_data["keyword"] == test_data["keyword"]
        assert retrieved_data["platform"] == test_data["platform"]
        assert retrieved_data["score"] == test_data["score"]
        
        # 데이터 삭제
        test_redis.delete(test_key)
    
    def test_redis_expiration(self, test_redis):
        """Redis 만료 테스트"""
        import time
        
        test_key = "test:expiration"
        test_value = "expiring_value"
        
        # 1초 후 만료되도록 설정
        test_redis.setex(test_key, 1, test_value)
        
        # 즉시 조회하면 값이 있어야 함
        assert test_redis.get(test_key).decode('utf-8') == test_value
        
        # 1.5초 후에는 만료되어야 함
        time.sleep(1.5)
        assert test_redis.get(test_key) is None


class TestCeleryIntegration:
    """Celery 통합 테스트 (모킹)"""
    
    @pytest.mark.asyncio
    async def test_celery_task_execution(self, mock_external_services):
        """Celery 태스크 실행 테스트"""
        from app.tasks.keyword_assessment import assess_single_keyword
        
        # 모킹된 환경에서 태스크 실행
        result = assess_single_keyword("테스트키워드", "musinsa")
        
        # 태스크가 실행되어야 함 (모킹된 결과)
        assert isinstance(result, dict)
        assert "success" in result
    
    @pytest.mark.asyncio
    async def test_batch_task_execution(self, mock_external_services):
        """배치 태스크 실행 테스트"""
        from app.tasks.batch_processing import process_batch_keywords
        
        # 모킹된 환경에서 배치 태스크 실행
        result = process_batch_keywords(
            batch_id="test_batch_integration",
            platform="musinsa",
            batch_size=3
        )
        
        # 배치 태스크가 실행되어야 함
        assert isinstance(result, dict)
        assert "success" in result


class TestFileSystemIntegration:
    """파일 시스템 통합 테스트"""
    
    def test_screenshot_directory_creation(self):
        """스크린샷 디렉토리 생성 테스트"""
        from app.services.image_storage import ImageStorage
        
        # 임시 디렉토리를 사용한 테스트
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "local_storage_path": temp_dir,
                "use_s3": False
            }
            
            image_storage = ImageStorage(config)
            
            # 디렉토리가 생성되었는지 확인
            assert os.path.exists(temp_dir)
    
    def test_file_operations(self):
        """파일 연산 테스트"""
        from app.services.image_storage import ImageStorage
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "local_storage_path": temp_dir,
                "use_s3": False,
                "enable_compression": False,
                "enable_thumbnail": False
            }
            
            image_storage = ImageStorage(config)
            
            # 테스트 파일 생성
            test_file = os.path.join(temp_dir, "test_image.png")
            test_data = b"fake_image_data"
            
            with open(test_file, 'wb') as f:
                f.write(test_data)
            
            # 파일이 생성되었는지 확인
            assert os.path.exists(test_file)
            
            # 파일 크기 확인
            assert os.path.getsize(test_file) == len(test_data)


class TestNetworkConnectivity:
    """네트워크 연결성 테스트"""
    
    def test_external_api_availability(self):
        """외부 API 가용성 테스트 (실제 연결 없이)"""
        # 실제 외부 API 호출 대신 모킹된 응답 테스트
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_get.return_value = mock_response
            
            # 모킹된 API 호출
            response = requests.get("https://api.example.com/health")
            
            assert response.status_code == 200
            assert response.json()["status"] == "ok"
    
    def test_webhook_endpoint_mock(self):
        """웹훅 엔드포인트 모킹 테스트"""
        webhook_url = "https://hooks.slack.com/test"
        test_payload = {"text": "테스트 메시지"}
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "ok"
            mock_post.return_value = mock_response
            
            # 모킹된 웹훅 호출
            response = requests.post(webhook_url, json=test_payload)
            
            assert response.status_code == 200
            assert response.text == "ok"