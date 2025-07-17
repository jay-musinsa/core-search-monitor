import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, date
from app.tasks.keyword_assessment import assess_single_keyword
from app.core.database import get_database_client


class TestKeywordAssessment:
    """키워드 평가 태스크 테스트"""
    
    def test_assess_single_keyword_success(self, mock_database_client, sample_keyword_data,
                                         sample_api_response, sample_gpt_response):
        """단일 키워드 평가 성공 테스트"""
        # Mock 데이터베이스 응답
        mock_database_client.query.return_value.result_rows = [[1, "테스트 키워드", "clothing", 1]]
        mock_database_client.insert.return_value = True
        
        # Mock API 서비스
        with patch('app.tasks.keyword_assessment.MusinsaAPIService') as mock_api_service:
            mock_api_instance = Mock()
            mock_api_instance.search_products.return_value = sample_api_response
            mock_api_service.return_value = mock_api_instance
            
            # Mock 크롤러
            with patch('app.tasks.keyword_assessment.UnifiedCrawler') as mock_crawler:
                mock_crawler_instance = Mock()
                mock_crawler_instance.capture_screenshot.return_value = {
                    "success": True,
                    "screenshot_path": "/tmp/test_screenshot.png",
                    "file_size": 1024,
                    "quality": "high"
                }
                mock_crawler.return_value = mock_crawler_instance
                
                # Mock GPT 서비스
                with patch('app.tasks.keyword_assessment.GPTService') as mock_gpt_service:
                    mock_gpt_instance = Mock()
                    mock_gpt_instance.evaluate_screenshot.return_value = sample_gpt_response
                    mock_gpt_service.return_value = mock_gpt_instance
                    
                    # 테스트 실행
                    result = assess_single_keyword("테스트 키워드", "musinsa")
                    
                    # 결과 검증
                    assert result["success"] == True
                    assert result["keyword"] == "테스트 키워드"
                    assert result["platform"] == "musinsa"
                    assert "processing_time" in result
                    assert "assessment_id" in result
    
    def test_assess_single_keyword_api_failure(self, mock_database_client):
        """API 호출 실패 테스트"""
        # Mock 데이터베이스 응답
        mock_database_client.query.return_value.result_rows = [[1, "테스트 키워드", "clothing", 1]]
        mock_database_client.insert.return_value = True
        
        # Mock API 서비스 실패
        with patch('app.tasks.keyword_assessment.MusinsaAPIService') as mock_api_service:
            mock_api_instance = Mock()
            mock_api_instance.search_products.side_effect = Exception("API Error")
            mock_api_service.return_value = mock_api_instance
            
            # 테스트 실행
            result = assess_single_keyword("테스트 키워드", "musinsa")
            
            # 결과 검증
            assert result["success"] == False
            assert "error" in result
            assert "API Error" in result["error"]
    
    def test_assess_single_keyword_screenshot_failure(self, mock_database_client,
                                                    sample_api_response):
        """스크린샷 캡처 실패 테스트"""
        # Mock 데이터베이스 응답
        mock_database_client.query.return_value.result_rows = [[1, "테스트 키워드", "clothing", 1]]
        mock_database_client.insert.return_value = True
        
        # Mock API 서비스
        with patch('app.tasks.keyword_assessment.MusinsaAPIService') as mock_api_service:
            mock_api_instance = Mock()
            mock_api_instance.search_products.return_value = sample_api_response
            mock_api_service.return_value = mock_api_instance
            
            # Mock 크롤러 실패
            with patch('app.tasks.keyword_assessment.UnifiedCrawler') as mock_crawler:
                mock_crawler_instance = Mock()
                mock_crawler_instance.capture_screenshot.return_value = {
                    "success": False,
                    "error": "Screenshot capture failed"
                }
                mock_crawler.return_value = mock_crawler_instance
                
                # 테스트 실행
                result = assess_single_keyword("테스트 키워드", "musinsa")
                
                # 결과 검증
                assert result["success"] == False
                assert "error" in result
                assert "Screenshot capture failed" in result["error"]
    
    def test_assess_single_keyword_gpt_failure(self, mock_database_client,
                                             sample_api_response):
        """GPT 평가 실패 테스트"""
        # Mock 데이터베이스 응답
        mock_database_client.query.return_value.result_rows = [[1, "테스트 키워드", "clothing", 1]]
        mock_database_client.insert.return_value = True
        
        # Mock API 서비스
        with patch('app.tasks.keyword_assessment.MusinsaAPIService') as mock_api_service:
            mock_api_instance = Mock()
            mock_api_instance.search_products.return_value = sample_api_response
            mock_api_service.return_value = mock_api_instance
            
            # Mock 크롤러
            with patch('app.tasks.keyword_assessment.UnifiedCrawler') as mock_crawler:
                mock_crawler_instance = Mock()
                mock_crawler_instance.capture_screenshot.return_value = {
                    "success": True,
                    "screenshot_path": "/tmp/test_screenshot.png",
                    "file_size": 1024,
                    "quality": "high"
                }
                mock_crawler.return_value = mock_crawler_instance
                
                # Mock GPT 서비스 실패
                with patch('app.tasks.keyword_assessment.GPTService') as mock_gpt_service:
                    mock_gpt_instance = Mock()
                    mock_gpt_instance.evaluate_screenshot.side_effect = Exception("GPT Error")
                    mock_gpt_service.return_value = mock_gpt_instance
                    
                    # 테스트 실행
                    result = assess_single_keyword("테스트 키워드", "musinsa")
                    
                    # 결과 검증
                    assert result["success"] == False
                    assert "error" in result
                    assert "GPT Error" in result["error"]
    
    def test_assess_single_keyword_database_failure(self, mock_database_client,
                                                  sample_api_response, sample_gpt_response):
        """데이터베이스 저장 실패 테스트"""
        # Mock 데이터베이스 응답 (키워드 조회 성공, 삽입 실패)
        mock_database_client.query.return_value.result_rows = [[1, "테스트 키워드", "clothing", 1]]
        mock_database_client.insert.side_effect = Exception("Database Error")
        
        # Mock API 서비스
        with patch('app.tasks.keyword_assessment.MusinsaAPIService') as mock_api_service:
            mock_api_instance = Mock()
            mock_api_instance.search_products.return_value = sample_api_response
            mock_api_service.return_value = mock_api_instance
            
            # Mock 크롤러
            with patch('app.tasks.keyword_assessment.UnifiedCrawler') as mock_crawler:
                mock_crawler_instance = Mock()
                mock_crawler_instance.capture_screenshot.return_value = {
                    "success": True,
                    "screenshot_path": "/tmp/test_screenshot.png",
                    "file_size": 1024,
                    "quality": "high"
                }
                mock_crawler.return_value = mock_crawler_instance
                
                # Mock GPT 서비스
                with patch('app.tasks.keyword_assessment.GPTService') as mock_gpt_service:
                    mock_gpt_instance = Mock()
                    mock_gpt_instance.evaluate_screenshot.return_value = sample_gpt_response
                    mock_gpt_service.return_value = mock_gpt_instance
                    
                    # 테스트 실행
                    result = assess_single_keyword("테스트 키워드", "musinsa")
                    
                    # 결과 검증
                    assert result["success"] == False
                    assert "error" in result
                    assert "Database Error" in result["error"]
    
    def test_assess_single_keyword_new_keyword_creation(self, mock_database_client,
                                                      sample_api_response, sample_gpt_response):
        """새 키워드 생성 테스트"""
        # Mock 데이터베이스 응답 (키워드 조회 실패 - 새 키워드 생성)
        mock_database_client.query.return_value.result_rows = []
        mock_database_client.insert.return_value = True
        
        # Mock API 서비스
        with patch('app.tasks.keyword_assessment.MusinsaAPIService') as mock_api_service:
            mock_api_instance = Mock()
            mock_api_instance.search_products.return_value = sample_api_response
            mock_api_service.return_value = mock_api_instance
            
            # Mock 크롤러
            with patch('app.tasks.keyword_assessment.UnifiedCrawler') as mock_crawler:
                mock_crawler_instance = Mock()
                mock_crawler_instance.capture_screenshot.return_value = {
                    "success": True,
                    "screenshot_path": "/tmp/test_screenshot.png",
                    "file_size": 1024,
                    "quality": "high"
                }
                mock_crawler.return_value = mock_crawler_instance
                
                # Mock GPT 서비스
                with patch('app.tasks.keyword_assessment.GPTService') as mock_gpt_service:
                    mock_gpt_instance = Mock()
                    mock_gpt_instance.evaluate_screenshot.return_value = sample_gpt_response
                    mock_gpt_service.return_value = mock_gpt_instance
                    
                    # UUID Mock
                    with patch('uuid.uuid4') as mock_uuid:
                        mock_uuid.return_value.hex = "abc123"
                        
                        # 테스트 실행
                        result = assess_single_keyword("새 키워드", "musinsa")
                        
                        # 결과 검증
                        assert result["success"] == True
                        assert "new_keyword_created" in result
                        assert result["new_keyword_created"] == True
    
    def test_assess_single_keyword_invalid_platform(self, mock_database_client):
        """잘못된 플랫폼 테스트"""
        # Mock 데이터베이스 응답
        mock_database_client.query.return_value.result_rows = [[1, "테스트 키워드", "clothing", 1]]
        
        # 테스트 실행
        result = assess_single_keyword("테스트 키워드", "invalid_platform")
        
        # 결과 검증
        assert result["success"] == False
        assert "error" in result
        assert "지원되지 않는 플랫폼" in result["error"]
    
    def test_assess_single_keyword_timing_measurement(self, mock_database_client,
                                                    sample_api_response, sample_gpt_response):
        """처리 시간 측정 테스트"""
        # Mock 데이터베이스 응답
        mock_database_client.query.return_value.result_rows = [[1, "테스트 키워드", "clothing", 1]]
        mock_database_client.insert.return_value = True
        
        # Mock API 서비스
        with patch('app.tasks.keyword_assessment.MusinsaAPIService') as mock_api_service:
            mock_api_instance = Mock()
            mock_api_instance.search_products.return_value = sample_api_response
            mock_api_service.return_value = mock_api_instance
            
            # Mock 크롤러
            with patch('app.tasks.keyword_assessment.UnifiedCrawler') as mock_crawler:
                mock_crawler_instance = Mock()
                mock_crawler_instance.capture_screenshot.return_value = {
                    "success": True,
                    "screenshot_path": "/tmp/test_screenshot.png",
                    "file_size": 1024,
                    "quality": "high"
                }
                mock_crawler.return_value = mock_crawler_instance
                
                # Mock GPT 서비스
                with patch('app.tasks.keyword_assessment.GPTService') as mock_gpt_service:
                    mock_gpt_instance = Mock()
                    mock_gpt_instance.evaluate_screenshot.return_value = sample_gpt_response
                    mock_gpt_service.return_value = mock_gpt_instance
                    
                    # 시간 Mock
                    with patch('time.time') as mock_time:
                        mock_time.side_effect = [1000, 1005]  # 5초 경과
                        
                        # 테스트 실행
                        result = assess_single_keyword("테스트 키워드", "musinsa")
                        
                        # 결과 검증
                        assert result["success"] == True
                        assert result["processing_time"] == 5.0
    
    def test_assess_single_keyword_retry_mechanism(self, mock_database_client):
        """재시도 메커니즘 테스트"""
        # Mock 데이터베이스 응답
        mock_database_client.query.return_value.result_rows = [[1, "테스트 키워드", "clothing", 1]]
        mock_database_client.insert.return_value = True
        
        # Mock API 서비스 (첫 번째 호출 실패, 두 번째 호출 성공)
        with patch('app.tasks.keyword_assessment.MusinsaAPIService') as mock_api_service:
            mock_api_instance = Mock()
            mock_api_instance.search_products.side_effect = [
                Exception("Temporary Error"),
                {"status": "success", "data": {"products": []}}
            ]
            mock_api_service.return_value = mock_api_instance
            
            # Mock 크롤러
            with patch('app.tasks.keyword_assessment.UnifiedCrawler') as mock_crawler:
                mock_crawler_instance = Mock()
                mock_crawler_instance.capture_screenshot.return_value = {
                    "success": True,
                    "screenshot_path": "/tmp/test_screenshot.png",
                    "file_size": 1024,
                    "quality": "high"
                }
                mock_crawler.return_value = mock_crawler_instance
                
                # Mock GPT 서비스
                with patch('app.tasks.keyword_assessment.GPTService') as mock_gpt_service:
                    mock_gpt_instance = Mock()
                    mock_gpt_instance.evaluate_screenshot.return_value = {
                        "ndcg_score": 0.5,
                        "precision": 0.5,
                        "recall": 0.5,
                        "relevance_score": 0.5,
                        "evaluation_text": "재시도 성공",
                        "confidence_score": 0.8
                    }
                    mock_gpt_service.return_value = mock_gpt_instance
                    
                    # 테스트 실행
                    result = assess_single_keyword("테스트 키워드", "musinsa")
                    
                    # 결과 검증
                    assert result["success"] == True
                    assert result["retry_count"] == 1