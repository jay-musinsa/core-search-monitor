"""
데이터베이스 통합 테스트
"""

import pytest
from datetime import date, datetime, timedelta
import json


class TestClickHouseIntegration:
    """ClickHouse 데이터베이스 통합 테스트"""
    
    def test_database_connection_and_queries(self, test_database):
        """데이터베이스 연결 및 기본 쿼리 테스트"""
        # 기본 연결 테스트
        result = test_database.query("SELECT 1 as test_value")
        assert result.result_rows[0][0] == 1
        
        # 현재 시간 조회
        result = test_database.query("SELECT now()")
        assert result.result_rows[0][0] is not None
    
    def test_keyword_master_operations(self, test_database):
        """키워드 마스터 테이블 운영 테스트"""
        # 데이터 조회
        result = test_database.query("SELECT COUNT(*) FROM keyword_master")
        initial_count = result.result_rows[0][0]
        assert initial_count > 0
        
        # 특정 키워드 조회
        result = test_database.query("SELECT * FROM keyword_master WHERE keyword = '테스트키워드1'")
        assert len(result.result_rows) > 0
        
        keyword_data = result.result_rows[0]
        assert keyword_data[1] == "테스트키워드1"  # keyword 컬럼
        assert keyword_data[2] == "clothing"  # category 컬럼
        assert keyword_data[4] == 1  # is_active 컬럼
    
    def test_quality_assessment_operations(self, test_database):
        """품질 평가 테이블 운영 테스트"""
        # 오늘 데이터 조회
        today = date.today()
        query = f"SELECT * FROM quality_assessment_daily WHERE assessment_date = '{today}'"
        result = test_database.query(query)
        
        assert len(result.result_rows) > 0
        
        # 첫 번째 레코드 검증
        assessment_data = result.result_rows[0]
        assert assessment_data[2] == today  # assessment_date
        assert assessment_data[3] in ["musinsa", "29cm"]  # platform
        assert 0 <= assessment_data[5] <= 1  # gpt_ndcg_score
    
    def test_batch_jobs_operations(self, test_database):
        """배치 작업 테이블 운영 테스트"""
        # 배치 작업 조회
        result = test_database.query("SELECT * FROM batch_jobs WHERE batch_id = 'test_batch_001'")
        assert len(result.result_rows) > 0
        
        batch_data = result.result_rows[0]
        assert batch_data[0] == "test_batch_001"  # batch_id
        assert batch_data[1] == "daily_assessment"  # job_type
        assert batch_data[2] == "completed"  # status
    
    def test_keyword_trends_operations(self, test_database):
        """키워드 트렌드 테이블 운영 테스트"""
        # 트렌드 데이터 조회
        result = test_database.query("SELECT * FROM keyword_trends WHERE keyword_id = 1")
        
        if len(result.result_rows) > 0:
            trend_data = result.result_rows[0]
            assert trend_data[0] == 1  # keyword_id
            assert trend_data[1] in ["musinsa", "29cm"]  # platform
            assert isinstance(trend_data[2], date)  # trend_date
    
    def test_system_metrics_operations(self, test_database):
        """시스템 메트릭 테이블 운영 테스트"""
        # 시스템 메트릭 조회
        result = test_database.query("SELECT * FROM system_metrics LIMIT 5")
        
        if len(result.result_rows) > 0:
            metric_data = result.result_rows[0]
            assert isinstance(metric_data[0], datetime)  # metric_time
            assert metric_data[1] in ["cpu", "memory", "disk", "api_latency", "network"]  # metric_type
            assert isinstance(metric_data[2], (int, float))  # metric_value


class TestDataConsistency:
    """데이터 일관성 테스트"""
    
    def test_foreign_key_relationships(self, test_database):
        """외래키 관계 일관성 테스트"""
        # 품질 평가 데이터의 키워드 ID가 키워드 마스터에 존재하는지 확인
        query = """
        SELECT qad.keyword_id, km.keyword
        FROM quality_assessment_daily qad
        LEFT JOIN keyword_master km ON qad.keyword_id = km.id
        WHERE km.id IS NULL
        LIMIT 1
        """
        
        result = test_database.query(query)
        # 고아 레코드가 없어야 함
        assert len(result.result_rows) == 0
    
    def test_data_integrity(self, test_database):
        """데이터 무결성 테스트"""
        # NDCG 점수가 0-1 범위 내에 있는지 확인
        query = """
        SELECT COUNT(*) 
        FROM quality_assessment_daily 
        WHERE gpt_ndcg_score < 0 OR gpt_ndcg_score > 1
        """
        
        result = test_database.query(query)
        invalid_scores = result.result_rows[0][0]
        assert invalid_scores == 0
        
        # Precision 점수가 0-1 범위 내에 있는지 확인
        query = """
        SELECT COUNT(*) 
        FROM quality_assessment_daily 
        WHERE gpt_precision < 0 OR gpt_precision > 1
        """
        
        result = test_database.query(query)
        invalid_precision = result.result_rows[0][0]
        assert invalid_precision == 0
    
    def test_date_consistency(self, test_database):
        """날짜 일관성 테스트"""
        # 미래 날짜의 데이터가 없는지 확인
        tomorrow = date.today() + timedelta(days=1)
        query = f"""
        SELECT COUNT(*) 
        FROM quality_assessment_daily 
        WHERE assessment_date > '{tomorrow}'
        """
        
        result = test_database.query(query)
        future_data = result.result_rows[0][0]
        assert future_data == 0
    
    def test_platform_consistency(self, test_database):
        """플랫폼 일관성 테스트"""
        # 지원되는 플랫폼만 있는지 확인
        query = """
        SELECT DISTINCT platform 
        FROM quality_assessment_daily
        """
        
        result = test_database.query(query)
        platforms = [row[0] for row in result.result_rows]
        
        valid_platforms = ["musinsa", "29cm"]
        for platform in platforms:
            assert platform in valid_platforms


class TestPerformanceQueries:
    """성능 관련 쿼리 테스트"""
    
    def test_index_performance(self, test_database):
        """인덱스 성능 테스트"""
        import time
        
        # 인덱스가 적용된 쿼리 성능 측정
        start_time = time.time()
        
        query = """
        SELECT km.keyword, qad.gpt_ndcg_score
        FROM keyword_master km
        JOIN quality_assessment_daily qad ON km.id = qad.keyword_id
        WHERE km.keyword = '테스트키워드1'
        AND qad.assessment_date >= today() - INTERVAL 7 DAY
        """
        
        result = test_database.query(query)
        end_time = time.time()
        
        query_time = end_time - start_time
        
        # 쿼리가 1초 이내에 완료되어야 함
        assert query_time < 1.0
        assert len(result.result_rows) >= 0
    
    def test_aggregation_performance(self, test_database):
        """집계 쿼리 성능 테스트"""
        import time
        
        start_time = time.time()
        
        query = """
        SELECT 
            platform,
            COUNT(*) as total_assessments,
            AVG(gpt_ndcg_score) as avg_ndcg,
            AVG(gpt_precision) as avg_precision,
            AVG(gpt_recall) as avg_recall
        FROM quality_assessment_daily
        WHERE assessment_date >= today() - INTERVAL 30 DAY
        GROUP BY platform
        """
        
        result = test_database.query(query)
        end_time = time.time()
        
        query_time = end_time - start_time
        
        # 집계 쿼리가 2초 이내에 완료되어야 함
        assert query_time < 2.0
        assert len(result.result_rows) >= 0
    
    def test_large_dataset_query(self, test_database):
        """대용량 데이터셋 쿼리 테스트"""
        # 모든 품질 평가 데이터 조회
        query = """
        SELECT COUNT(*) 
        FROM quality_assessment_daily
        """
        
        result = test_database.query(query)
        total_records = result.result_rows[0][0]
        
        # 테스트 데이터가 있어야 함
        assert total_records > 0


class TestComplexQueries:
    """복잡한 쿼리 테스트"""
    
    def test_trend_analysis_query(self, test_database):
        """트렌드 분석 쿼리 테스트"""
        query = """
        SELECT 
            km.keyword,
            km.category,
            qad.platform,
            qad.assessment_date,
            qad.gpt_ndcg_score,
            LAG(qad.gpt_ndcg_score, 1) OVER (
                PARTITION BY qad.keyword_id, qad.platform 
                ORDER BY qad.assessment_date
            ) as prev_ndcg_score
        FROM keyword_master km
        JOIN quality_assessment_daily qad ON km.id = qad.keyword_id
        WHERE qad.assessment_date >= today() - INTERVAL 7 DAY
        ORDER BY km.keyword, qad.platform, qad.assessment_date
        """
        
        result = test_database.query(query)
        
        # 복잡한 윈도우 함수 쿼리가 성공해야 함
        assert len(result.result_rows) >= 0
    
    def test_anomaly_detection_query(self, test_database):
        """이상치 탐지 쿼리 테스트"""
        query = """
        WITH stats AS (
            SELECT 
                keyword_id,
                platform,
                AVG(gpt_ndcg_score) as avg_score,
                stddevPop(gpt_ndcg_score) as std_score
            FROM quality_assessment_daily
            WHERE assessment_date >= today() - INTERVAL 7 DAY
            GROUP BY keyword_id, platform
        )
        SELECT 
            qad.keyword_id,
            qad.platform,
            qad.gpt_ndcg_score,
            stats.avg_score,
            ABS(qad.gpt_ndcg_score - stats.avg_score) / stats.std_score as z_score
        FROM quality_assessment_daily qad
        JOIN stats ON qad.keyword_id = stats.keyword_id AND qad.platform = stats.platform
        WHERE ABS(qad.gpt_ndcg_score - stats.avg_score) / stats.std_score > 2
        AND qad.assessment_date = today()
        """
        
        result = test_database.query(query)
        
        # 이상치 탐지 쿼리가 성공해야 함
        assert len(result.result_rows) >= 0
    
    def test_performance_comparison_query(self, test_database):
        """성능 비교 쿼리 테스트"""
        query = """
        SELECT 
            km.keyword,
            km.category,
            musinsa.gpt_ndcg_score as musinsa_score,
            cm.gpt_ndcg_score as cm_score,
            musinsa.gpt_ndcg_score - cm.gpt_ndcg_score as score_diff
        FROM keyword_master km
        LEFT JOIN (
            SELECT keyword_id, gpt_ndcg_score
            FROM quality_assessment_daily
            WHERE platform = 'musinsa' AND assessment_date = today()
        ) musinsa ON km.id = musinsa.keyword_id
        LEFT JOIN (
            SELECT keyword_id, gpt_ndcg_score
            FROM quality_assessment_daily
            WHERE platform = '29cm' AND assessment_date = today()
        ) cm ON km.id = cm.keyword_id
        WHERE musinsa.gpt_ndcg_score IS NOT NULL 
        AND cm.gpt_ndcg_score IS NOT NULL
        """
        
        result = test_database.query(query)
        
        # 플랫폼 간 성능 비교 쿼리가 성공해야 함
        assert len(result.result_rows) >= 0


class TestDataModification:
    """데이터 수정 테스트"""
    
    def test_insert_and_cleanup(self, test_database, clean_database):
        """데이터 삽입 및 정리 테스트"""
        # 테스트 키워드 삽입
        test_keyword_id = 9999
        insert_query = f"""
        INSERT INTO keyword_master (id, keyword, category, priority, is_active)
        VALUES ({test_keyword_id}, '통합테스트키워드', 'test', 1, 1)
        """
        
        test_database.query(insert_query)
        
        # 삽입된 데이터 확인
        select_query = f"SELECT * FROM keyword_master WHERE id = {test_keyword_id}"
        result = test_database.query(select_query)
        
        assert len(result.result_rows) == 1
        assert result.result_rows[0][1] == "통합테스트키워드"
        
        # 데이터 삭제
        delete_query = f"DELETE FROM keyword_master WHERE id = {test_keyword_id}"
        test_database.query(delete_query)
        
        # 삭제 확인
        result = test_database.query(select_query)
        assert len(result.result_rows) == 0
    
    def test_update_operations(self, test_database):
        """업데이트 연산 테스트"""
        # 기존 데이터의 우선순위 업데이트
        keyword_id = 1
        
        # 현재 우선순위 확인
        select_query = f"SELECT priority FROM keyword_master WHERE id = {keyword_id}"
        result = test_database.query(select_query)
        original_priority = result.result_rows[0][0]
        
        # 우선순위 업데이트
        new_priority = original_priority + 1
        update_query = f"""
        ALTER TABLE keyword_master 
        UPDATE priority = {new_priority}
        WHERE id = {keyword_id}
        """
        
        test_database.query(update_query)
        
        # 업데이트 확인
        result = test_database.query(select_query)
        updated_priority = result.result_rows[0][0]
        assert updated_priority == new_priority
        
        # 원복
        restore_query = f"""
        ALTER TABLE keyword_master 
        UPDATE priority = {original_priority}
        WHERE id = {keyword_id}
        """
        
        test_database.query(restore_query)