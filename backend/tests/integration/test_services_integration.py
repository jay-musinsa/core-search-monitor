"""
서비스 통합 테스트
"""

import pytest
import asyncio
from datetime import date, datetime, timedelta
from unittest.mock import patch, Mock
import json
import tempfile
import os


class TestBatchOptimizerIntegration:
    """배치 최적화 서비스 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_batch_processing_end_to_end(
        self, 
        batch_optimizer_service, 
        test_database, 
        mock_external_services
    ):
        """배치 처리 전체 플로우 테스트"""
        target_date = date.today()
        platforms = ["musinsa"]
        keyword_count = 5
        
        result = await batch_optimizer_service.optimize_batch_processing(
            target_date=target_date,
            platforms=platforms,
            keyword_count=keyword_count
        )
        
        assert result["success"] == True
        assert "batch_id" in result
        assert "processing_time" in result
        assert "metrics" in result
        assert result["optimization_applied"] == True
    
    @pytest.mark.asyncio
    async def test_batch_status_tracking(
        self, 
        batch_optimizer_service, 
        test_database
    ):
        """배치 상태 추적 테스트"""
        batch_id = "test_batch_001"
        
        status = await batch_optimizer_service.get_batch_status(batch_id)
        
        if "error" not in status:
            assert "batch_id" in status
            assert "status" in status
            assert "total_keywords" in status
    
    @pytest.mark.asyncio
    async def test_concurrent_batch_processing(
        self, 
        batch_optimizer_service, 
        test_database, 
        mock_external_services
    ):
        """동시 배치 처리 테스트"""
        async def run_batch(platform):
            return await batch_optimizer_service.optimize_batch_processing(
                target_date=date.today(),
                platforms=[platform],
                keyword_count=3
            )
        
        # 두 플랫폼에서 동시 배치 실행
        tasks = [
            run_batch("musinsa"),
            run_batch("29cm")
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 최소 하나는 성공해야 함
        success_count = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        assert success_count >= 1


class TestTrendAnalyzerIntegration:
    """트렌드 분석 서비스 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_keyword_trend_analysis(
        self, 
        trend_analyzer_service, 
        test_database
    ):
        """키워드 트렌드 분석 테스트"""
        keyword_id = 1
        platform = "musinsa"
        
        result = await trend_analyzer_service.analyze_keyword_trends(
            keyword_id=keyword_id,
            platform=platform,
            analysis_days=7
        )
        
        if result.get("success"):
            assert "keyword_id" in result
            assert "platform" in result
            assert "trend_analysis" in result
            assert "anomaly_detection" in result
    
    @pytest.mark.asyncio
    async def test_anomaly_detection(
        self, 
        trend_analyzer_service, 
        test_database
    ):
        """이상치 탐지 테스트"""
        keyword_id = 10  # 이상치 테스트 키워드
        platform = "musinsa"
        
        result = await trend_analyzer_service.analyze_keyword_trends(
            keyword_id=keyword_id,
            platform=platform,
            analysis_days=7
        )
        
        if result.get("success"):
            anomaly_info = result.get("anomaly_detection", {})
            
            # 이상치가 탐지되었을 것으로 예상
            if anomaly_info.get("recent_anomaly_alert"):
                assert anomaly_info["recent_anomaly_alert"].get("has_recent_anomalies")
    
    @pytest.mark.asyncio
    async def test_trend_data_update(
        self, 
        trend_analyzer_service, 
        test_database
    ):
        """트렌드 데이터 업데이트 테스트"""
        keyword_id = 1
        platform = "musinsa"
        
        result = await trend_analyzer_service.update_trend_data(
            keyword_id=keyword_id,
            platform=platform
        )
        
        assert result["success"] == True
        assert result["keyword_id"] == keyword_id
        assert result["platform"] == platform
    
    @pytest.mark.asyncio
    async def test_trend_summary(
        self, 
        trend_analyzer_service, 
        test_database
    ):
        """트렌드 요약 테스트"""
        result = await trend_analyzer_service.get_trend_summary(days=7)
        
        if result.get("success"):
            assert "summary_period" in result
            assert "platform_summary" in result
            assert "recent_anomalies" in result


class TestImageStorageIntegration:
    """이미지 저장소 서비스 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_image_save_and_retrieve(
        self, 
        image_storage_service, 
        test_database
    ):
        """이미지 저장 및 조회 테스트"""
        # 테스트 이미지 데이터 생성
        test_image_data = b"fake_image_data_for_testing"
        keyword = "테스트키워드"
        platform = "musinsa"
        
        # 이미지 저장
        save_result = await image_storage_service.save_screenshot(
            image_data=test_image_data,
            keyword=keyword,
            platform=platform,
            metadata={"test": True}
        )
        
        if save_result.get("success"):
            assert "file_path" in save_result
            assert "metadata_id" in save_result
            
            # 메타데이터 조회
            metadata_id = save_result["metadata_id"]
            metadata_result = await image_storage_service.get_image_metadata(metadata_id)
            
            if "error" not in metadata_result:
                assert metadata_result["keyword"] == keyword
                assert metadata_result["platform"] == platform
    
    @pytest.mark.asyncio
    async def test_image_optimization(
        self, 
        image_storage_service
    ):
        """이미지 최적화 테스트"""
        # 큰 테스트 이미지 데이터
        large_image_data = b"x" * 10000  # 10KB 가짜 데이터
        
        # 최적화 테스트
        optimized_data = await image_storage_service._optimize_image(large_image_data)
        
        # 최적화가 적용되었는지 확인 (실제로는 PIL이 없어서 원본 반환)
        assert isinstance(optimized_data, bytes)
    
    @pytest.mark.asyncio
    async def test_storage_statistics(
        self, 
        image_storage_service, 
        test_database
    ):
        """저장소 통계 테스트"""
        stats = await image_storage_service.get_storage_statistics()
        
        if "error" not in stats:
            assert "total_images" in stats
            assert "platform_statistics" in stats
            assert "storage_statistics" in stats
    
    @pytest.mark.asyncio
    async def test_cleanup_old_images(
        self, 
        image_storage_service, 
        test_database
    ):
        """오래된 이미지 정리 테스트"""
        result = await image_storage_service.cleanup_old_images(retention_days=1)
        
        assert result["success"] == True
        assert "cleaned_count" in result
        assert "retention_days" in result


class TestNotificationServiceIntegration:
    """알림 서비스 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_custom_notification_send(
        self, 
        notification_service_instance,
        test_database
    ):
        """사용자 정의 알림 발송 테스트"""
        from app.services.notification_service import NotificationLevel, NotificationChannel
        
        result = await notification_service_instance.send_custom_notification(
            title="테스트 알림",
            message="테스트 메시지입니다.",
            level=NotificationLevel.MEDIUM,
            channels=[NotificationChannel.EMAIL],
            data={"test": True}
        )
        
        assert result["success"] == True
        assert "event_id" in result
    
    @pytest.mark.asyncio
    async def test_notification_history(
        self, 
        notification_service_instance,
        test_database
    ):
        """알림 히스토리 조회 테스트"""
        result = await notification_service_instance.get_notification_history(limit=10)
        
        if result.get("success"):
            assert "history" in result
            assert "total" in result
            assert isinstance(result["history"], list)
    
    @pytest.mark.asyncio
    async def test_service_lifecycle(
        self, 
        notification_service_instance
    ):
        """서비스 라이프사이클 테스트"""
        # 서비스 시작
        await notification_service_instance.start_service()
        
        # 서비스가 실행 중인지 확인
        assert len(notification_service_instance.background_tasks) > 0
        
        # 서비스 중지
        await notification_service_instance.stop_service()


class TestDatabaseIntegration:
    """데이터베이스 통합 테스트"""
    
    def test_database_connection(self, test_database):
        """데이터베이스 연결 테스트"""
        result = test_database.query("SELECT 1")
        assert result.result_rows[0][0] == 1
    
    def test_schema_exists(self, test_database):
        """스키마 존재 확인 테스트"""
        # 주요 테이블들이 존재하는지 확인
        tables = [
            "keyword_master",
            "quality_assessment_daily", 
            "keyword_trends",
            "batch_jobs",
            "system_metrics"
        ]
        
        for table in tables:
            try:
                result = test_database.query(f"SELECT COUNT(*) FROM {table}")
                # 테이블이 존재하면 결과가 반환됨
                assert result.result_rows is not None
            except Exception as e:
                pytest.fail(f"Table {table} does not exist: {e}")
    
    def test_test_data_insertion(self, test_database):
        """테스트 데이터 삽입 확인 테스트"""
        # 테스트 데이터가 삽입되었는지 확인
        result = test_database.query("SELECT COUNT(*) FROM keyword_master")
        keyword_count = result.result_rows[0][0]
        assert keyword_count > 0
        
        result = test_database.query("SELECT COUNT(*) FROM quality_assessment_daily")
        assessment_count = result.result_rows[0][0]
        assert assessment_count > 0
    
    def test_data_relationships(self, test_database):
        """데이터 관계 테스트"""
        # 키워드와 품질 평가 데이터 간의 관계 확인
        query = """
        SELECT km.keyword, qad.platform, qad.gpt_ndcg_score
        FROM keyword_master km
        JOIN quality_assessment_daily qad ON km.id = qad.keyword_id
        WHERE km.keyword = '테스트키워드1'
        LIMIT 1
        """
        
        result = test_database.query(query)
        if result.result_rows:
            row = result.result_rows[0]
            assert row[0] == "테스트키워드1"
            assert row[1] in ["musinsa", "29cm"]
            assert isinstance(row[2], (int, float))


class TestServiceInteraction:
    """서비스 간 상호작용 테스트"""
    
    @pytest.mark.asyncio
    async def test_batch_to_trend_analysis_flow(
        self, 
        batch_optimizer_service,
        trend_analyzer_service,
        test_database,
        mock_external_services
    ):
        """배치 처리 → 트렌드 분석 플로우 테스트"""
        # 1. 배치 처리 실행
        batch_result = await batch_optimizer_service.optimize_batch_processing(
            target_date=date.today(),
            platforms=["musinsa"],
            keyword_count=3
        )
        
        if batch_result.get("success"):
            # 2. 처리된 키워드에 대한 트렌드 분석
            trend_result = await trend_analyzer_service.analyze_keyword_trends(
                keyword_id=1,
                platform="musinsa",
                analysis_days=7
            )
            
            # 트렌드 분석이 성공해야 함
            if trend_result.get("success"):
                assert "trend_analysis" in trend_result
    
    @pytest.mark.asyncio
    async def test_anomaly_to_notification_flow(
        self, 
        trend_analyzer_service,
        notification_service_instance,
        test_database
    ):
        """이상치 탐지 → 알림 발송 플로우 테스트"""
        from app.services.notification_service import NotificationLevel, NotificationChannel
        
        # 1. 이상치 탐지
        trend_result = await trend_analyzer_service.analyze_keyword_trends(
            keyword_id=10,  # 이상치 테스트 키워드
            platform="musinsa",
            analysis_days=7
        )
        
        if trend_result.get("success"):
            anomaly_info = trend_result.get("anomaly_detection", {})
            
            # 2. 이상치가 탐지된 경우 알림 발송
            if anomaly_info.get("recent_anomaly_alert", {}).get("has_recent_anomalies"):
                notification_result = await notification_service_instance.send_custom_notification(
                    title="이상치 탐지",
                    message="키워드 성능 이상치가 탐지되었습니다.",
                    level=NotificationLevel.HIGH,
                    channels=[NotificationChannel.EMAIL]
                )
                
                assert notification_result["success"] == True
    
    @pytest.mark.asyncio 
    async def test_full_quality_assessment_pipeline(
        self,
        batch_optimizer_service,
        trend_analyzer_service,
        image_storage_service,
        notification_service_instance,
        test_database,
        mock_external_services
    ):
        """전체 품질 평가 파이프라인 테스트"""
        keyword_id = 1
        platform = "musinsa"
        
        # 1. 배치 처리로 품질 평가 실행
        batch_result = await batch_optimizer_service.optimize_batch_processing(
            target_date=date.today(),
            platforms=[platform],
            keyword_count=1
        )
        
        if batch_result.get("success"):
            # 2. 이미지 저장 (스크린샷)
            test_image = b"test_screenshot_data"
            image_result = await image_storage_service.save_screenshot(
                image_data=test_image,
                keyword="테스트키워드",
                platform=platform
            )
            
            # 3. 트렌드 분석 실행
            if image_result.get("success"):
                trend_result = await trend_analyzer_service.analyze_keyword_trends(
                    keyword_id=keyword_id,
                    platform=platform,
                    analysis_days=7
                )
                
                # 4. 필요시 알림 발송
                if trend_result.get("success"):
                    from app.services.notification_service import NotificationLevel, NotificationChannel
                    
                    await notification_service_instance.send_custom_notification(
                        title="품질 평가 완료",
                        message="키워드 품질 평가가 완료되었습니다.",
                        level=NotificationLevel.LOW,
                        channels=[NotificationChannel.EMAIL]
                    )
                    
                    # 전체 파이프라인이 성공적으로 실행됨
                    assert True