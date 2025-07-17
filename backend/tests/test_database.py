import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
import asyncio
from app.core.database import (
    DatabaseManager,
    get_database_client,
    init_database,
    get_keyword_by_id,
    save_quality_assessment,
    get_batch_job_status,
    update_batch_job_status
)


class TestDatabaseManager:
    """데이터베이스 매니저 테스트"""
    
    @pytest.fixture
    def db_manager(self):
        """데이터베이스 매니저 인스턴스"""
        return DatabaseManager()
    
    def test_database_manager_initialization(self, db_manager):
        """데이터베이스 매니저 초기화 테스트"""
        assert db_manager is not None
        assert hasattr(db_manager, 'client')
        assert hasattr(db_manager, 'connection_pool')
    
    @patch('clickhouse_connect.get_client')
    def test_get_database_client_success(self, mock_get_client):
        """데이터베이스 클라이언트 연결 성공 테스트"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        client = get_database_client()
        
        assert client == mock_client
        mock_get_client.assert_called_once()
    
    @patch('clickhouse_connect.get_client')
    def test_get_database_client_failure(self, mock_get_client):
        """데이터베이스 클라이언트 연결 실패 테스트"""
        mock_get_client.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception) as exc_info:
            get_database_client()
        
        assert "Connection failed" in str(exc_info.value)
    
    def test_get_keyword_by_id_success(self, mock_database_client):
        """키워드 ID로 조회 성공 테스트"""
        # Mock 데이터베이스 응답
        mock_database_client.query.return_value.result_rows = [
            [1, "테스트 키워드", "clothing", 1, 1, "2024-01-01 00:00:00", "2024-01-01 00:00:00"]
        ]
        
        # 테스트 실행
        result = get_keyword_by_id(1)
        
        # 결과 검증
        assert result["success"] == True
        assert result["keyword"]["id"] == 1
        assert result["keyword"]["keyword"] == "테스트 키워드"
        assert result["keyword"]["category"] == "clothing"
        assert result["keyword"]["priority"] == 1
        assert result["keyword"]["is_active"] == 1
    
    def test_get_keyword_by_id_not_found(self, mock_database_client):
        """키워드 ID로 조회 실패 테스트"""
        # Mock 데이터베이스 응답 (결과 없음)
        mock_database_client.query.return_value.result_rows = []
        
        # 테스트 실행
        result = get_keyword_by_id(999)
        
        # 결과 검증
        assert result["success"] == False
        assert "error" in result
        assert "키워드를 찾을 수 없습니다" in result["error"]
    
    def test_get_keyword_by_id_database_error(self, mock_database_client):
        """키워드 조회 데이터베이스 오류 테스트"""
        # Mock 데이터베이스 오류
        mock_database_client.query.side_effect = Exception("Database query failed")
        
        # 테스트 실행
        result = get_keyword_by_id(1)
        
        # 결과 검증
        assert result["success"] == False
        assert "error" in result
        assert "Database query failed" in result["error"]
    
    def test_save_quality_assessment_success(self, mock_database_client):
        """품질 평가 결과 저장 성공 테스트"""
        # Mock 데이터베이스 응답
        mock_database_client.insert.return_value = True
        
        # 테스트 데이터
        assessment_data = {
            "keyword_id": 1,
            "assessment_date": date.today(),
            "platform": "musinsa",
            "api_response_time": 1.5,
            "api_total_results": 100,
            "api_status_code": 200,
            "api_response_data": '{"products": []}',
            "gpt_ndcg_score": 0.85,
            "gpt_precision": 0.80,
            "gpt_recall": 0.75,
            "gpt_relevance_score": 0.82,
            "gpt_evaluation_text": "검색 결과가 키워드와 관련성이 높음",
            "gpt_confidence_score": 0.90,
            "screenshot_path": "/tmp/screenshot.png",
            "screenshot_size": 1024,
            "screenshot_quality": "high",
            "processing_time": 5.0,
            "batch_id": "test_batch_001",
            "retry_count": 0,
            "error_message": ""
        }
        
        # 테스트 실행
        result = save_quality_assessment(assessment_data)
        
        # 결과 검증
        assert result["success"] == True
        assert "assessment_id" in result
        mock_database_client.insert.assert_called_once()
    
    def test_save_quality_assessment_database_error(self, mock_database_client):
        """품질 평가 결과 저장 실패 테스트"""
        # Mock 데이터베이스 오류
        mock_database_client.insert.side_effect = Exception("Insert failed")
        
        # 테스트 데이터
        assessment_data = {
            "keyword_id": 1,
            "assessment_date": date.today(),
            "platform": "musinsa",
            "api_response_time": 1.5,
            "api_total_results": 100,
            "api_status_code": 200,
            "gpt_ndcg_score": 0.85,
            "gpt_precision": 0.80,
            "gpt_recall": 0.75,
            "processing_time": 5.0,
            "batch_id": "test_batch_001"
        }
        
        # 테스트 실행
        result = save_quality_assessment(assessment_data)
        
        # 결과 검증
        assert result["success"] == False
        assert "error" in result
        assert "Insert failed" in result["error"]
    
    def test_get_batch_job_status_success(self, mock_database_client):
        """배치 작업 상태 조회 성공 테스트"""
        # Mock 데이터베이스 응답
        mock_database_client.query.return_value.result_rows = [
            [
                "test_batch_001",
                "daily_assessment",
                "completed",
                100,
                95,
                5,
                datetime(2024, 1, 1, 9, 0, 0),
                datetime(2024, 1, 1, 9, 0, 0),
                datetime(2024, 1, 1, 10, 0, 0),
                "",
                "Batch completed successfully",
                2.5,
                950,
                15.75
            ]
        ]
        
        # 테스트 실행
        result = get_batch_job_status("test_batch_001")
        
        # 결과 검증
        assert result["success"] == True
        assert result["batch_id"] == "test_batch_001"
        assert result["job_type"] == "daily_assessment"
        assert result["status"] == "completed"
        assert result["total_keywords"] == 100
        assert result["processed_keywords"] == 95
        assert result["failed_keywords"] == 5
        assert result["avg_processing_time"] == 2.5
        assert result["gpt_api_calls"] == 950
        assert result["gpt_api_cost"] == 15.75
    
    def test_update_batch_job_status_success(self, mock_database_client):
        """배치 작업 상태 업데이트 성공 테스트"""
        # Mock 데이터베이스 응답
        mock_database_client.query.return_value = True
        
        # 테스트 실행
        result = update_batch_job_status(
            batch_id="test_batch_001",
            status="running",
            processed_keywords=50,
            failed_keywords=2,
            avg_processing_time=2.5,
            gpt_api_calls=500,
            gpt_api_cost=7.50
        )
        
        # 결과 검증
        assert result["success"] == True
        assert result["batch_id"] == "test_batch_001"
        assert result["status"] == "running"
        mock_database_client.query.assert_called_once()
    
    def test_connection_pool_management(self, db_manager):
        """연결 풀 관리 테스트"""
        with patch('clickhouse_connect.get_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # 여러 번 클라이언트 요청
            client1 = db_manager.get_client()
            client2 = db_manager.get_client()
            
            # 같은 클라이언트 인스턴스 반환 확인
            assert client1 == client2
            assert mock_get_client.call_count == 1
    
    def test_query_with_retry_success(self, mock_database_client):
        """쿼리 재시도 성공 테스트"""
        # Mock 데이터베이스 응답 (첫 번째 실패, 두 번째 성공)
        mock_database_client.query.side_effect = [
            Exception("Temporary connection error"),
            Mock(result_rows=[[1, "테스트 키워드", "clothing", 1]])
        ]
        
        # 테스트 실행
        result = get_keyword_by_id(1)
        
        # 결과 검증
        assert result["success"] == True
        assert result["keyword"]["id"] == 1
        assert mock_database_client.query.call_count == 2
    
    def test_query_with_retry_max_attempts(self, mock_database_client):
        """쿼리 재시도 최대 횟수 테스트"""
        # Mock 데이터베이스 응답 (계속 실패)
        mock_database_client.query.side_effect = Exception("Persistent connection error")
        
        # 테스트 실행
        result = get_keyword_by_id(1)
        
        # 결과 검증
        assert result["success"] == False
        assert "error" in result
        assert mock_database_client.query.call_count == 3  # 최대 3번 재시도
    
    def test_transaction_management(self, mock_database_client):
        """트랜잭션 관리 테스트"""
        # Mock 트랜잭션 메서드
        mock_database_client.begin_transaction = Mock()
        mock_database_client.commit_transaction = Mock()
        mock_database_client.rollback_transaction = Mock()
        
        assessment_data = {
            "keyword_id": 1,
            "assessment_date": date.today(),
            "platform": "musinsa",
            "processing_time": 5.0,
            "batch_id": "test_batch_001"
        }
        
        # 성공 케이스
        mock_database_client.insert.return_value = True
        
        result = save_quality_assessment(assessment_data)
        
        assert result["success"] == True
    
    def test_data_validation(self, mock_database_client):
        """데이터 유효성 검증 테스트"""
        # 잘못된 데이터
        invalid_assessment_data = {
            "keyword_id": "invalid_id",  # 문자열 (숫자여야 함)
            "assessment_date": "invalid_date",  # 잘못된 날짜 형식
            "platform": "",  # 빈 문자열
            "gpt_ndcg_score": 1.5,  # 범위 초과 (0-1 사이여야 함)
            "processing_time": -1.0,  # 음수 (양수여야 함)
        }
        
        # 테스트 실행
        result = save_quality_assessment(invalid_assessment_data)
        
        # 결과 검증
        assert result["success"] == False
        assert "error" in result
        assert "유효성 검증 실패" in result["error"]
    
    @pytest.mark.asyncio
    async def test_async_operations(self, mock_database_client):
        """비동기 작업 테스트"""
        # Mock 비동기 메서드
        mock_database_client.query_async = AsyncMock()
        mock_database_client.query_async.return_value.result_rows = [
            [1, "테스트 키워드", "clothing", 1]
        ]
        
        # 비동기 함수 테스트
        async def async_get_keyword(keyword_id):
            return await mock_database_client.query_async(
                f"SELECT * FROM keyword_master WHERE id = {keyword_id}"
            )
        
        result = await async_get_keyword(1)
        
        assert result.result_rows[0][0] == 1
        assert result.result_rows[0][1] == "테스트 키워드"
    
    def test_performance_monitoring(self, mock_database_client):
        """성능 모니터링 테스트"""
        # Mock 성능 메트릭
        mock_database_client.query.return_value.result_rows = [
            [1, "테스트 키워드", "clothing", 1]
        ]
        
        # 시간 Mock
        with patch('time.time') as mock_time:
            mock_time.side_effect = [1000, 1002]  # 2초 경과
            
            # 성능 측정 포함 쿼리
            result = get_keyword_by_id(1)
            
            # 결과 검증
            assert result["success"] == True
            assert "query_time" in result
            assert result["query_time"] == 2.0