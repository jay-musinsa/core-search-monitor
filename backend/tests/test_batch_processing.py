import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
from app.tasks.batch_processing import (
    process_batch_keywords,
    daily_keyword_assessment,
    get_batch_status,
    start_batch_processing
)


class TestBatchProcessing:
    """배치 처리 테스트"""
    
    def test_process_batch_keywords_success(self, mock_database_client, sample_batch_job):
        """배치 키워드 처리 성공 테스트"""
        # Mock 데이터베이스 응답
        mock_database_client.query.return_value.result_rows = [
            [1, "키워드1", "clothing", 1],
            [2, "키워드2", "shoes", 1],
            [3, "키워드3", "bags", 1]
        ]
        mock_database_client.insert.return_value = True
        
        # Mock 키워드 평가 태스크
        with patch('app.tasks.batch_processing.assess_single_keyword') as mock_assess:
            mock_assess.return_value = {
                "success": True,
                "keyword": "테스트 키워드",
                "platform": "musinsa",
                "processing_time": 2.5,
                "assessment_id": "abc123"
            }
            
            # 테스트 실행
            result = process_batch_keywords(
                batch_id="test_batch_001",
                platform="musinsa",
                batch_size=10
            )
            
            # 결과 검증
            assert result["success"] == True
            assert result["total_processed"] == 3
            assert result["successful_assessments"] == 3
            assert result["failed_assessments"] == 0
            assert result["batch_id"] == "test_batch_001"
    
    def test_process_batch_keywords_partial_failure(self, mock_database_client):
        """배치 처리 부분 실패 테스트"""
        # Mock 데이터베이스 응답
        mock_database_client.query.return_value.result_rows = [
            [1, "키워드1", "clothing", 1],
            [2, "키워드2", "shoes", 1],
            [3, "키워드3", "bags", 1]
        ]
        mock_database_client.insert.return_value = True
        
        # Mock 키워드 평가 태스크 (일부 실패)
        with patch('app.tasks.batch_processing.assess_single_keyword') as mock_assess:
            mock_assess.side_effect = [
                {"success": True, "keyword": "키워드1", "platform": "musinsa"},
                {"success": False, "keyword": "키워드2", "error": "API Error"},
                {"success": True, "keyword": "키워드3", "platform": "musinsa"}
            ]
            
            # 테스트 실행
            result = process_batch_keywords(
                batch_id="test_batch_001",
                platform="musinsa",
                batch_size=10
            )
            
            # 결과 검증
            assert result["success"] == True
            assert result["total_processed"] == 3
            assert result["successful_assessments"] == 2
            assert result["failed_assessments"] == 1
            assert len(result["failed_keywords"]) == 1
            assert result["failed_keywords"][0] == "키워드2"
    
    def test_process_batch_keywords_database_error(self, mock_database_client):
        """데이터베이스 오류 테스트"""
        # Mock 데이터베이스 오류
        mock_database_client.query.side_effect = Exception("Database connection failed")
        
        # 테스트 실행
        result = process_batch_keywords(
            batch_id="test_batch_001",
            platform="musinsa",
            batch_size=10
        )
        
        # 결과 검증
        assert result["success"] == False
        assert "error" in result
        assert "Database connection failed" in result["error"]
    
    def test_daily_keyword_assessment_success(self, mock_database_client):
        """일일 키워드 평가 성공 테스트"""
        # Mock 데이터베이스 응답
        mock_database_client.query.return_value.result_rows = [
            [1, "키워드1", "clothing", 1],
            [2, "키워드2", "shoes", 1]
        ]
        mock_database_client.insert.return_value = True
        
        # Mock 배치 처리
        with patch('app.tasks.batch_processing.process_batch_keywords') as mock_process:
            mock_process.return_value = {
                "success": True,
                "total_processed": 2,
                "successful_assessments": 2,
                "failed_assessments": 0,
                "processing_time": 120.0
            }
            
            # 테스트 실행
            result = daily_keyword_assessment(
                target_date=date.today(),
                platforms=["musinsa"],
                batch_size=10
            )
            
            # 결과 검증
            assert result["success"] == True
            assert result["total_keywords"] == 2
            assert result["total_successful"] == 2
            assert result["total_failed"] == 0
            assert "batch_jobs" in result
            assert len(result["batch_jobs"]) == 1
    
    def test_daily_keyword_assessment_multiple_platforms(self, mock_database_client):
        """다중 플랫폼 일일 평가 테스트"""
        # Mock 데이터베이스 응답
        mock_database_client.query.return_value.result_rows = [
            [1, "키워드1", "clothing", 1],
            [2, "키워드2", "shoes", 1]
        ]
        mock_database_client.insert.return_value = True
        
        # Mock 배치 처리
        with patch('app.tasks.batch_processing.process_batch_keywords') as mock_process:
            mock_process.return_value = {
                "success": True,
                "total_processed": 2,
                "successful_assessments": 2,
                "failed_assessments": 0,
                "processing_time": 120.0
            }
            
            # 테스트 실행
            result = daily_keyword_assessment(
                target_date=date.today(),
                platforms=["musinsa", "29cm"],
                batch_size=10
            )
            
            # 결과 검증
            assert result["success"] == True
            assert len(result["batch_jobs"]) == 2
            assert result["total_keywords"] == 4  # 2 keywords × 2 platforms
    
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
        assert result["status"] == "completed"
        assert result["total_keywords"] == 100
        assert result["processed_keywords"] == 95
        assert result["failed_keywords"] == 5
        assert result["processing_time"] == 3600.0  # 1시간 (초 단위)
    
    def test_get_batch_job_status_not_found(self, mock_database_client):
        """배치 작업 상태 조회 실패 테스트"""
        # Mock 데이터베이스 응답 (결과 없음)
        mock_database_client.query.return_value.result_rows = []
        
        # 테스트 실행
        result = get_batch_job_status("non_existent_batch")
        
        # 결과 검증
        assert result["success"] == False
        assert "error" in result
        assert "배치 작업을 찾을 수 없습니다" in result["error"]
    
    def test_update_batch_job_status_success(self, mock_database_client):
        """배치 작업 상태 업데이트 성공 테스트"""
        # Mock 데이터베이스 응답
        mock_database_client.query.return_value = True
        
        # 테스트 실행
        result = update_batch_job_status(
            batch_id="test_batch_001",
            status="running",
            processed_keywords=50,
            failed_keywords=2
        )
        
        # 결과 검증
        assert result["success"] == True
        assert result["batch_id"] == "test_batch_001"
        assert result["status"] == "running"
    
    def test_update_batch_job_status_database_error(self, mock_database_client):
        """배치 작업 상태 업데이트 실패 테스트"""
        # Mock 데이터베이스 오류
        mock_database_client.query.side_effect = Exception("Database update failed")
        
        # 테스트 실행
        result = update_batch_job_status(
            batch_id="test_batch_001",
            status="running",
            processed_keywords=50,
            failed_keywords=2
        )
        
        # 결과 검증
        assert result["success"] == False
        assert "error" in result
        assert "Database update failed" in result["error"]
    
    def test_batch_processing_with_priority_keywords(self, mock_database_client):
        """우선순위 키워드 배치 처리 테스트"""
        # Mock 데이터베이스 응답 (우선순위 순서)
        mock_database_client.query.return_value.result_rows = [
            [1, "고우선순위키워드", "clothing", 1],
            [2, "중우선순위키워드", "shoes", 2],
            [3, "저우선순위키워드", "bags", 3]
        ]
        mock_database_client.insert.return_value = True
        
        # Mock 키워드 평가 태스크
        with patch('app.tasks.batch_processing.assess_single_keyword') as mock_assess:
            mock_assess.return_value = {
                "success": True,
                "keyword": "테스트 키워드",
                "platform": "musinsa",
                "processing_time": 2.5
            }
            
            # 테스트 실행
            result = process_batch_keywords(
                batch_id="test_batch_001",
                platform="musinsa",
                batch_size=10,
                priority_only=True
            )
            
            # 결과 검증
            assert result["success"] == True
            assert result["total_processed"] == 3
    
    def test_batch_processing_performance_metrics(self, mock_database_client):
        """배치 처리 성능 메트릭 테스트"""
        # Mock 데이터베이스 응답
        mock_database_client.query.return_value.result_rows = [
            [1, "키워드1", "clothing", 1],
            [2, "키워드2", "shoes", 1]
        ]
        mock_database_client.insert.return_value = True
        
        # Mock 키워드 평가 태스크
        with patch('app.tasks.batch_processing.assess_single_keyword') as mock_assess:
            mock_assess.return_value = {
                "success": True,
                "keyword": "테스트 키워드",
                "platform": "musinsa",
                "processing_time": 2.5,
                "gpt_api_calls": 1,
                "gpt_api_cost": 0.05
            }
            
            # 시간 Mock
            with patch('time.time') as mock_time:
                mock_time.side_effect = [1000, 1010]  # 10초 경과
                
                # 테스트 실행
                result = process_batch_keywords(
                    batch_id="test_batch_001",
                    platform="musinsa",
                    batch_size=10
                )
                
                # 결과 검증
                assert result["success"] == True
                assert result["total_processing_time"] == 10.0
                assert result["avg_processing_time"] == 5.0  # 10초 / 2개
                assert result["total_gpt_api_calls"] == 2
                assert result["total_gpt_api_cost"] == 0.10
    
    def test_batch_processing_error_handling(self, mock_database_client):
        """배치 처리 에러 처리 테스트"""
        # Mock 데이터베이스 응답
        mock_database_client.query.return_value.result_rows = [
            [1, "키워드1", "clothing", 1],
            [2, "키워드2", "shoes", 1]
        ]
        mock_database_client.insert.return_value = True
        
        # Mock 키워드 평가 태스크 (예외 발생)
        with patch('app.tasks.batch_processing.assess_single_keyword') as mock_assess:
            mock_assess.side_effect = [
                {"success": True, "keyword": "키워드1", "platform": "musinsa"},
                Exception("Unexpected error")
            ]
            
            # 테스트 실행
            result = process_batch_keywords(
                batch_id="test_batch_001",
                platform="musinsa",
                batch_size=10
            )
            
            # 결과 검증
            assert result["success"] == True
            assert result["total_processed"] == 2
            assert result["successful_assessments"] == 1
            assert result["failed_assessments"] == 1
            assert len(result["failed_keywords"]) == 1
            assert result["failed_keywords"][0] == "키워드2"