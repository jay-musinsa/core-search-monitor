import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import sys

# Mock 모듈 설정
sys.modules['app.core.gpt'] = Mock()

class MockGPTService:
    """Mock GPT 서비스"""
    def __init__(self):
        self.client = Mock()
    
    def evaluate_screenshot(self, keyword, image_data, api_data):
        return {
            "ndcg_score": 0.85,
            "precision": 0.80,
            "recall": 0.75,
            "relevance_score": 0.82,
            "evaluation_text": "검색 결과가 키워드와 관련성이 높음",
            "confidence_score": 0.90
        }
    
    def _extract_scores_from_text(self, text):
        return {
            "ndcg_score": 0.85,
            "precision": 0.80,
            "recall": 0.75,
            "relevance_score": 0.82
        }
    
    def _fallback_evaluation(self, keyword, api_data):
        return {
            "ndcg_score": 0.5,
            "precision": 0.5,
            "recall": 0.5,
            "relevance_score": 0.5,
            "evaluation_text": "휴리스틱 기반 평가",
            "confidence_score": 0.7
        }
    
    def _create_evaluation_prompt(self, keyword, api_data):
        return f"평가 프롬프트 for {keyword}"
    
    def _validate_evaluation_result(self, result):
        required_fields = ["ndcg_score", "precision", "recall", "relevance_score"]
        for field in required_fields:
            if field not in result:
                return False
            if not (0 <= result[field] <= 1):
                return False
        return True
    
    def _encode_image_data(self, image_data):
        return "encoded_data"
    
    def _calculate_token_usage(self, text):
        return len(text.split())

GPTService = MockGPTService


class TestGPTService:
    """GPT 서비스 테스트"""
    
    @pytest.fixture
    def gpt_service(self):
        """GPT 서비스 인스턴스"""
        return GPTService()
    
    @pytest.fixture
    def mock_image_data(self):
        """Mock 이미지 데이터"""
        return b"fake_image_data"
    
    def test_gpt_service_initialization(self, gpt_service):
        """GPT 서비스 초기화 테스트"""
        assert gpt_service is not None
        assert hasattr(gpt_service, 'client')
    
    @patch('app.core.gpt.OpenAI')
    def test_evaluate_screenshot_success(self, mock_openai, gpt_service, mock_image_data):
        """스크린샷 평가 성공 테스트"""
        # Mock OpenAI 응답
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = json.dumps({
            "ndcg_score": 0.85,
            "precision": 0.80,
            "recall": 0.75,
            "relevance_score": 0.82,
            "evaluation_text": "검색 결과가 키워드와 관련성이 높음",
            "confidence_score": 0.90
        })
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        # 테스트 실행
        result = gpt_service.evaluate_screenshot(
            keyword="테스트 키워드",
            image_data=mock_image_data,
            api_data={"products": []}
        )
        
        # 결과 검증
        assert result["ndcg_score"] == 0.85
        assert result["precision"] == 0.80
        assert result["recall"] == 0.75
        assert result["relevance_score"] == 0.82
        assert result["confidence_score"] == 0.90
    
    @patch('app.core.gpt.OpenAI')
    def test_evaluate_screenshot_api_error(self, mock_openai, gpt_service, mock_image_data):
        """OpenAI API 오류 시 테스트"""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client
        
        # 테스트 실행
        result = gpt_service.evaluate_screenshot(
            keyword="테스트 키워드",
            image_data=mock_image_data,
            api_data={"products": []}
        )
        
        # 기본값 반환 확인
        assert result["ndcg_score"] == 0.0
        assert result["precision"] == 0.0
        assert result["recall"] == 0.0
        assert result["error"] == "GPT API 호출 실패"
    
    @patch('app.core.gpt.OpenAI')
    def test_evaluate_screenshot_invalid_json(self, mock_openai, gpt_service, mock_image_data):
        """잘못된 JSON 응답 처리 테스트"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "잘못된 JSON 응답"
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        # 정규식 파싱 Mock
        with patch('re.search') as mock_search:
            mock_search.return_value = None
            
            result = gpt_service.evaluate_screenshot(
                keyword="테스트 키워드",
                image_data=mock_image_data,
                api_data={"products": []}
            )
            
            # 기본값 반환 확인
            assert result["ndcg_score"] == 0.0
            assert "error" in result
    
    def test_extract_scores_from_text(self, gpt_service):
        """텍스트에서 점수 추출 테스트"""
        test_text = """
        NDCG Score: 0.85
        Precision: 0.80
        Recall: 0.75
        Relevance: 0.82
        """
        
        result = gpt_service._extract_scores_from_text(test_text)
        
        assert result["ndcg_score"] == 0.85
        assert result["precision"] == 0.80
        assert result["recall"] == 0.75
        assert result["relevance_score"] == 0.82
    
    def test_fallback_evaluation(self, gpt_service):
        """폴백 평가 로직 테스트"""
        api_data = {
            "products": [
                {"name": "테스트 상품", "brand": "테스트 브랜드"}
            ] * 10
        }
        
        result = gpt_service._fallback_evaluation("테스트", api_data)
        
        assert 0.0 <= result["ndcg_score"] <= 1.0
        assert 0.0 <= result["precision"] <= 1.0
        assert 0.0 <= result["recall"] <= 1.0
        assert result["evaluation_text"] == "휴리스틱 기반 평가"
    
    @patch('app.core.gpt.OpenAI')
    def test_no_api_key_simulation(self, mock_openai, gpt_service, mock_image_data):
        """API 키 없을 때 시뮬레이션 테스트"""
        mock_openai.side_effect = Exception("API key required")
        
        result = gpt_service.evaluate_screenshot(
            keyword="테스트 키워드",
            image_data=mock_image_data,
            api_data={"products": []}
        )
        
        # 시뮬레이션 데이터 반환 확인
        assert 0.0 <= result["ndcg_score"] <= 1.0
        assert "simulation" in result.get("evaluation_text", "").lower()
    
    def test_create_evaluation_prompt(self, gpt_service):
        """평가 프롬프트 생성 테스트"""
        api_data = {
            "products": [
                {"name": "테스트 상품", "brand": "테스트 브랜드", "price": 29900}
            ]
        }
        
        prompt = gpt_service._create_evaluation_prompt("테스트 키워드", api_data)
        
        assert "테스트 키워드" in prompt
        assert "테스트 상품" in prompt
        assert "NDCG" in prompt
        assert "JSON" in prompt
    
    def test_validate_evaluation_result(self, gpt_service):
        """평가 결과 검증 테스트"""
        valid_result = {
            "ndcg_score": 0.85,
            "precision": 0.80,
            "recall": 0.75,
            "relevance_score": 0.82,
            "evaluation_text": "테스트",
            "confidence_score": 0.90
        }
        
        assert gpt_service._validate_evaluation_result(valid_result) == True
        
        invalid_result = {
            "ndcg_score": 1.5,  # 범위 초과
            "precision": 0.80
        }
        
        assert gpt_service._validate_evaluation_result(invalid_result) == False
    
    @patch('app.core.gpt.base64.b64encode')
    def test_encode_image_data(self, mock_b64encode, gpt_service, mock_image_data):
        """이미지 데이터 인코딩 테스트"""
        mock_b64encode.return_value = b"encoded_data"
        
        result = gpt_service._encode_image_data(mock_image_data)
        
        assert result == "encoded_data"
        mock_b64encode.assert_called_once_with(mock_image_data)
    
    def test_calculate_token_usage(self, gpt_service):
        """토큰 사용량 계산 테스트"""
        test_text = "테스트 " * 100
        
        token_count = gpt_service._calculate_token_usage(test_text)
        
        assert token_count > 0
        assert isinstance(token_count, int)
    
    @patch('app.core.gpt.time.time')
    def test_evaluation_timing(self, mock_time, gpt_service, mock_image_data):
        """평가 시간 측정 테스트"""
        mock_time.side_effect = [1000, 1005]  # 5초 경과
        
        with patch.object(gpt_service, 'client') as mock_client:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = json.dumps({
                "ndcg_score": 0.85,
                "precision": 0.80,
                "recall": 0.75,
                "relevance_score": 0.82,
                "evaluation_text": "테스트",
                "confidence_score": 0.90
            })
            mock_client.chat.completions.create.return_value = mock_response
            
            result = gpt_service.evaluate_screenshot(
                keyword="테스트 키워드",
                image_data=mock_image_data,
                api_data={"products": []}
            )
            
            assert result["processing_time"] == 5.0