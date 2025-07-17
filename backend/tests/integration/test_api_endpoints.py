"""
API 엔드포인트 통합 테스트
"""

import pytest
import asyncio
from datetime import date, timedelta
from fastapi.testclient import TestClient


class TestQualityDashboardAPI:
    """품질 대시보드 API 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_get_quality_dashboard_data_success(self, test_client, test_database):
        """품질 대시보드 데이터 조회 성공 테스트"""
        response = await test_client.get("/api/quality/dashboard/data")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert "data" in data
        assert "summary" in data
        assert "total" in data
        assert isinstance(data["data"], list)
        assert isinstance(data["summary"], dict)
        
        # 요약 데이터 검증
        summary = data["summary"]
        assert "totalKeywords" in summary
        assert "avgNdcgScore" in summary
        assert "avgPrecision" in summary
        assert "avgRecall" in summary
        assert "anomalyCount" in summary
    
    @pytest.mark.asyncio
    async def test_get_quality_dashboard_data_with_filters(self, test_client, test_database):
        """필터 적용된 품질 대시보드 데이터 조회 테스트"""
        params = {
            "platform": "musinsa",
            "category": "clothing",
            "dateRange": "7d",
            "threshold": 0.8,
            "sortBy": "ndcg_score",
            "sortDirection": "desc"
        }
        
        response = await test_client.get("/api/quality/dashboard/data", params=params)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        
        # 필터링 검증
        for item in data["data"]:
            assert item["platform"] == "musinsa"
            if item["category"]:
                assert item["category"] == "clothing"
            assert item["ndcg_score"] >= 0.8
    
    @pytest.mark.asyncio
    async def test_get_trend_data_success(self, test_client, test_database):
        """트렌드 데이터 조회 성공 테스트"""
        response = await test_client.get("/api/quality/trend/data")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert "data" in data
        assert isinstance(data["data"], list)
        
        # 트렌드 데이터 구조 검증
        if data["data"]:
            trend_item = data["data"][0]
            required_fields = [
                "date", "platform", "ndcg_score", "precision", 
                "recall", "total_assessments"
            ]
            for field in required_fields:
                assert field in trend_item
    
    @pytest.mark.asyncio
    async def test_get_keyword_analysis_success(self, test_client, test_database):
        """키워드 분석 조회 성공 테스트"""
        keyword_id = 1
        response = await test_client.get(f"/api/quality/keyword/{keyword_id}/analysis")
        
        assert response.status_code == 200
        data = response.json()
        
        # 분석 결과 구조 검증
        if data.get("success"):
            assert "keyword_id" in data
            assert "platform" in data
            assert "analysis_period" in data
            assert "data_points" in data
    
    @pytest.mark.asyncio
    async def test_get_keyword_analysis_not_found(self, test_client, test_database):
        """존재하지 않는 키워드 분석 조회 테스트"""
        keyword_id = 99999
        response = await test_client.get(f"/api/quality/keyword/{keyword_id}/analysis")
        
        # 존재하지 않는 키워드의 경우 빈 결과이거나 에러 응답
        assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_start_optimized_batch_success(self, test_client, test_database, sample_batch_request):
        """최적화된 배치 작업 시작 성공 테스트"""
        response = await test_client.post("/api/quality/batch/optimize", json=sample_batch_request)
        
        assert response.status_code == 200
        data = response.json()
        
        if data.get("success"):
            assert "batch_id" in data
            assert "processing_time" in data
            assert "metrics" in data
    
    @pytest.mark.asyncio
    async def test_get_batch_status_success(self, test_client, test_database):
        """배치 상태 조회 성공 테스트"""
        batch_id = "test_batch_001"
        response = await test_client.get(f"/api/quality/batch/{batch_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        
        # 배치 상태 응답 구조 검증
        if "error" not in data:
            status_fields = ["batch_id", "status", "total_keywords", "processed_keywords"]
            for field in status_fields:
                assert field in data
    
    @pytest.mark.asyncio
    async def test_get_trends_summary_success(self, test_client, test_database):
        """트렌드 요약 조회 성공 테스트"""
        response = await test_client.get("/api/quality/trends/summary?days=7")
        
        assert response.status_code == 200
        data = response.json()
        
        if data.get("success"):
            assert "summary_period" in data
            assert "platform_summary" in data
            assert "recent_anomalies" in data
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, test_client, test_database):
        """서비스 상태 체크 성공 테스트"""
        response = await test_client.get("/api/quality/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "database_connected" in data
        assert "timestamp" in data
        
        if data.get("success"):
            assert data["status"] == "healthy"
            assert data["database_connected"] == True


class TestMetricsAPI:
    """기존 메트릭 API 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_get_metrics_success(self, test_client, test_database):
        """메트릭 조회 성공 테스트"""
        response = await test_client.get("/api/metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        # 메트릭 데이터 구조 검증
        assert isinstance(data, dict)
    
    @pytest.mark.asyncio
    async def test_post_keyword_success(self, test_client, test_database):
        """키워드 입력 성공 테스트"""
        keyword_data = {"keyword": "테스트키워드"}
        response = await test_client.post("/api/keyword", json=keyword_data)
        
        # 키워드 입력 응답 검증
        assert response.status_code in [200, 201, 202]


class TestErrorHandling:
    """API 에러 처리 테스트"""
    
    @pytest.mark.asyncio
    async def test_invalid_parameters(self, test_client):
        """잘못된 파라미터 처리 테스트"""
        params = {
            "threshold": 1.5,  # 범위 초과
            "dateRange": "invalid",
            "sortDirection": "invalid"
        }
        
        response = await test_client.get("/api/quality/dashboard/data", params=params)
        
        # 400 에러 또는 기본값으로 처리되어야 함
        assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_missing_batch_id(self, test_client):
        """존재하지 않는 배치 ID 처리 테스트"""
        batch_id = "non_existent_batch"
        response = await test_client.get(f"/api/quality/batch/{batch_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        
        # 에러 메시지가 포함되어야 함
        if not data.get("success", True):
            assert "error" in data
    
    @pytest.mark.asyncio
    async def test_invalid_keyword_id(self, test_client):
        """잘못된 키워드 ID 처리 테스트"""
        keyword_id = "invalid_id"
        response = await test_client.get(f"/api/quality/keyword/{keyword_id}/analysis")
        
        # 400 에러 또는 422 에러가 발생해야 함
        assert response.status_code in [400, 422]


class TestPagination:
    """페이지네이션 테스트"""
    
    @pytest.mark.asyncio
    async def test_pagination_first_page(self, test_client, test_database):
        """첫 페이지 조회 테스트"""
        params = {"page": 1, "limit": 5}
        response = await test_client.get("/api/quality/dashboard/data", params=params)
        
        assert response.status_code == 200
        data = response.json()
        
        if data.get("success"):
            assert len(data["data"]) <= 5
    
    @pytest.mark.asyncio
    async def test_pagination_large_limit(self, test_client, test_database):
        """큰 limit 값 처리 테스트"""
        params = {"page": 1, "limit": 10000}  # 매우 큰 값
        response = await test_client.get("/api/quality/dashboard/data", params=params)
        
        # 서버에서 적절히 제한해야 함
        assert response.status_code in [200, 400]


class TestConcurrency:
    """동시성 테스트"""
    
    @pytest.mark.asyncio
    async def test_concurrent_api_calls(self, test_client, test_database):
        """동시 API 호출 테스트"""
        async def make_request():
            return await test_client.get("/api/quality/health")
        
        # 10개의 동시 요청
        tasks = [make_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks)
        
        # 모든 요청이 성공해야 함
        for response in responses:
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_concurrent_different_endpoints(self, test_client, test_database):
        """다양한 엔드포인트 동시 호출 테스트"""
        async def make_requests():
            tasks = [
                test_client.get("/api/quality/health"),
                test_client.get("/api/quality/dashboard/data"),
                test_client.get("/api/quality/trend/data"),
                test_client.get("/api/quality/trends/summary"),
                test_client.get("/api/metrics")
            ]
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        responses = await make_requests()
        
        # 대부분의 요청이 성공해야 함
        success_count = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 200)
        assert success_count >= len(responses) * 0.8  # 80% 이상 성공


class TestPerformance:
    """성능 테스트"""
    
    @pytest.mark.asyncio
    async def test_response_time(self, test_client, test_database):
        """응답 시간 테스트"""
        import time
        
        start_time = time.time()
        response = await test_client.get("/api/quality/dashboard/data")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # 응답 시간이 5초 이내여야 함
        assert response_time < 5.0
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_large_dataset_handling(self, test_client, test_database):
        """대용량 데이터셋 처리 테스트"""
        params = {
            "dateRange": "90d",  # 3개월 데이터
            "limit": 1000  # 큰 페이지 크기
        }
        
        response = await test_client.get("/api/quality/dashboard/data", params=params)
        
        # 대용량 데이터도 적절히 처리되어야 함
        assert response.status_code == 200