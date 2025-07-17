-- 키워드 품질평가 시스템을 위한 ClickHouse 스키마
-- 생성일: 2025-07-17
-- 목적: 매일 15,000개 키워드에 대한 품질평가 결과 저장 및 추이 분석

-- 1. 키워드 마스터 테이블
CREATE TABLE IF NOT EXISTS keyword_master (
    id UInt32,
    keyword String,
    category String,
    priority UInt8 DEFAULT 1,
    is_active UInt8 DEFAULT 1,
    created_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY id
SETTINGS index_granularity = 8192;

-- 2. 일일 품질평가 결과 테이블
CREATE TABLE IF NOT EXISTS quality_assessment_daily (
    id UInt64,
    keyword_id UInt32,
    assessment_date Date,
    platform String, -- 'musinsa', '29cm'
    
    -- API 응답 메트릭스
    api_response_time Float32,
    api_total_results UInt32,
    api_status_code UInt16,
    api_response_data String, -- JSON 형태로 저장
    
    -- GPT 평가 결과
    gpt_ndcg_score Float32,
    gpt_precision Float32,
    gpt_recall Float32,
    gpt_relevance_score Float32,
    gpt_evaluation_text String,
    gpt_confidence_score Float32,
    
    -- 스크린샷 정보
    screenshot_path String,
    screenshot_size UInt32,
    screenshot_quality String, -- 'high', 'medium', 'low'
    
    -- 처리 메타데이터
    processing_time Float32,
    batch_id String,
    retry_count UInt8 DEFAULT 0,
    error_message String DEFAULT '',
    
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(assessment_date)
ORDER BY (keyword_id, assessment_date, platform)
SETTINGS index_granularity = 8192;

-- 3. 키워드별 추이 분석 테이블
CREATE TABLE IF NOT EXISTS keyword_trends (
    keyword_id UInt32,
    platform String,
    trend_date Date,
    
    -- 이동평균 메트릭스
    ndcg_7day_avg Float32,
    ndcg_30day_avg Float32,
    precision_7day_avg Float32,
    precision_30day_avg Float32,
    
    -- 변화율 계산
    ndcg_change_rate Float32,
    precision_change_rate Float32,
    relevance_change_rate Float32,
    
    -- 이상치 탐지
    is_anomaly UInt8 DEFAULT 0,
    anomaly_score Float32 DEFAULT 0,
    anomaly_type String DEFAULT '', -- 'spike', 'drop', 'trend_change'
    
    -- 통계 정보
    data_points_count UInt32,
    confidence_interval Float32,
    
    updated_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (keyword_id, platform, trend_date)
SETTINGS index_granularity = 8192;

-- 4. 배치 작업 관리 테이블
CREATE TABLE IF NOT EXISTS batch_jobs (
    batch_id String,
    job_type String, -- 'daily_assessment', 'trend_analysis', 'anomaly_detection'
    status String, -- 'pending', 'running', 'completed', 'failed'
    
    -- 작업 세부정보
    total_keywords UInt32,
    processed_keywords UInt32,
    failed_keywords UInt32,
    
    -- 시간 정보
    scheduled_at DateTime,
    started_at Nullable(DateTime),
    completed_at Nullable(DateTime),
    
    -- 에러 및 로그
    error_message String DEFAULT '',
    log_data String DEFAULT '',
    
    -- 성능 메트릭스
    avg_processing_time Float32,
    gpt_api_calls UInt32,
    gpt_api_cost Float32,
    
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (batch_id, created_at)
SETTINGS index_granularity = 8192;

-- 5. 시스템 성능 모니터링 테이블
CREATE TABLE IF NOT EXISTS system_metrics (
    metric_time DateTime,
    metric_type String, -- 'cpu', 'memory', 'disk', 'network', 'api_latency'
    metric_value Float32,
    metric_unit String,
    
    -- 컨텍스트 정보
    component String, -- 'backend', 'celery', 'redis', 'clickhouse'
    environment String DEFAULT 'production',
    
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(metric_time)
ORDER BY (metric_time, metric_type)
SETTINGS index_granularity = 8192;

-- 인덱스 생성
-- 키워드 검색 최적화
CREATE INDEX IF NOT EXISTS idx_keyword_master_keyword ON keyword_master (keyword) TYPE bloom_filter(0.01);
CREATE INDEX IF NOT EXISTS idx_keyword_master_category ON keyword_master (category) TYPE bloom_filter(0.01);

-- 일일 평가 결과 검색 최적화
CREATE INDEX IF NOT EXISTS idx_quality_assessment_batch ON quality_assessment_daily (batch_id) TYPE bloom_filter(0.01);
CREATE INDEX IF NOT EXISTS idx_quality_assessment_date_range ON quality_assessment_daily (assessment_date) TYPE minmax;

-- 추이 분석 최적화
CREATE INDEX IF NOT EXISTS idx_keyword_trends_anomaly ON keyword_trends (is_anomaly) TYPE bloom_filter(0.01);

-- 배치 작업 상태 검색 최적화
CREATE INDEX IF NOT EXISTS idx_batch_jobs_status ON batch_jobs (status) TYPE bloom_filter(0.01);

-- 뷰 생성: 키워드별 최신 품질 점수  
CREATE VIEW IF NOT EXISTS v_keyword_latest_scores AS
SELECT 
    km.keyword,
    km.category,
    qad.platform,
    qad.gpt_ndcg_score,
    qad.gpt_precision,
    qad.gpt_recall,
    qad.assessment_date,
    qad.created_at
FROM keyword_master km
JOIN quality_assessment_daily qad ON km.id = qad.keyword_id
WHERE km.is_active = 1 
AND qad.assessment_date >= today() - INTERVAL 30 DAY
AND (qad.keyword_id, qad.platform, qad.assessment_date) IN (
    SELECT keyword_id, platform, max(assessment_date) as max_date
    FROM quality_assessment_daily
    WHERE assessment_date >= today() - INTERVAL 30 DAY
    GROUP BY keyword_id, platform
);

-- 뷰 생성: 일일 성과 요약
CREATE VIEW IF NOT EXISTS v_daily_performance_summary AS
SELECT 
    assessment_date,
    platform,
    count() as total_assessments,
    avg(gpt_ndcg_score) as avg_ndcg,
    avg(gpt_precision) as avg_precision,
    avg(gpt_recall) as avg_recall,
    avg(processing_time) as avg_processing_time,
    sum(gpt_ndcg_score > 0.8) as high_quality_count,
    sum(error_message != '') as error_count
FROM quality_assessment_daily
GROUP BY assessment_date, platform
ORDER BY assessment_date DESC, platform;

-- 뷰 생성: 이상치 알림 대시보드
CREATE VIEW IF NOT EXISTS v_anomaly_alerts AS
SELECT 
    kt.keyword_id,
    km.keyword,
    km.category,
    kt.platform,
    kt.trend_date,
    kt.anomaly_type,
    kt.anomaly_score,
    kt.ndcg_change_rate,
    kt.precision_change_rate,
    qad.gpt_ndcg_score as current_score,
    qad.gpt_precision as current_precision
FROM keyword_trends kt
JOIN keyword_master km ON kt.keyword_id = km.id
LEFT JOIN quality_assessment_daily qad ON (
    kt.keyword_id = qad.keyword_id 
    AND kt.platform = qad.platform 
    AND kt.trend_date = qad.assessment_date
)
WHERE kt.is_anomaly = 1
AND kt.trend_date >= today() - INTERVAL 7 DAY;

-- 성능 최적화를 위한 설정
-- 자동 압축 설정
ALTER TABLE quality_assessment_daily MODIFY SETTING merge_with_ttl_timeout = 3600;
ALTER TABLE system_metrics MODIFY SETTING merge_with_ttl_timeout = 1800;

-- TTL 설정 (데이터 보존 정책)
-- 시스템 메트릭스는 3개월 후 삭제
ALTER TABLE system_metrics MODIFY TTL metric_time + INTERVAL 3 MONTH;

-- 품질 평가 결과는 2년 후 압축
ALTER TABLE quality_assessment_daily MODIFY TTL assessment_date + INTERVAL 2 YEAR;

-- 초기 데이터 삽입 (샘플 키워드)
INSERT INTO keyword_master (id, keyword, category, priority) VALUES
(1, '원피스', 'clothing', 1),
(2, '청바지', 'clothing', 1),
(3, '운동화', 'shoes', 1),
(4, '백팩', 'bags', 2),
(5, '시계', 'accessories', 2);

-- 성능 모니터링을 위한 통계 정보 활성화
SET allow_experimental_analyzer = 1;
SET optimize_use_implicit_projections = 1;

-- 주석: 이 스키마는 다음과 같은 특징을 가집니다:
-- 1. 파티셔닝을 통한 쿼리 성능 최적화
-- 2. 적절한 인덱스를 통한 검색 성능 향상
-- 3. 뷰를 통한 복잡한 쿼리 단순화
-- 4. TTL을 통한 자동 데이터 관리
-- 5. 대용량 데이터 처리에 최적화된 구조