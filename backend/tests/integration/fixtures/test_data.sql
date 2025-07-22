-- 테스트 데이터 삽입 스크립트

-- 키워드 마스터 테스트 데이터
INSERT INTO keyword_master (id, keyword, category, priority, is_active, created_at, updated_at) VALUES
(1, '테스트키워드1', 'clothing', 1, 1, now(), now()),
(2, '테스트키워드2', 'shoes', 1, 1, now(), now()),
(3, '테스트키워드3', 'bags', 2, 1, now(), now()),
(4, '테스트키워드4', 'accessories', 2, 1, now(), now()),
(5, '테스트키워드5', 'clothing', 3, 1, now(), now()),
(6, '비활성키워드', 'clothing', 1, 0, now(), now()),
(7, '고우선순위키워드', 'shoes', 1, 1, now(), now()),
(8, '저우선순위키워드', 'bags', 3, 1, now(), now()),
(9, '성능테스트키워드', 'accessories', 1, 1, now(), now()),
(10, '이상치테스트키워드', 'clothing', 2, 1, now(), now());

-- 품질 평가 테스트 데이터
INSERT INTO quality_assessment_daily (
    id, keyword_id, assessment_date, platform,
    api_response_time, api_total_results, api_status_code, api_response_data,
    ndcg_score, precision_score, recall_score, confidence_score,
    evaluation_method, evaluation_details,
    ndcg_reason, precision_reason, recall_reason, precision_issues,
    gpt_ndcg_score, gpt_precision, gpt_recall, gpt_relevance_score, 
    gpt_evaluation_text, gpt_confidence_score,
    screenshot_path, screenshot_size, screenshot_quality,
    processing_time, batch_id, retry_count, error_message, created_at
) VALUES
-- 최근 데이터 (오늘)
(1, 1, today(), 'musinsa', 1.2, 50, 200, '{"total": 50, "products": []}',
 0.85, 0.80, 0.75, 0.90, 'Composite', '{"individual_results": {"llm": {"ndcg_10": 0.85}}, "weighting_strategy": "confidence_weighted"}',
 '검색 결과가 키워드와 관련성이 높음', '정확도가 우수함', '재현율이 양호함', '[{"goods_no": "123", "goods_name": "테스트상품", "reason": "테스트"}]',
 0.85, 0.80, 0.75, 0.82, '검색 결과가 키워드와 관련성이 높음', 0.90,
 '/screenshots/test_1.png', 1024, 'high', 3.5, 'test_batch_001', 0, '', now()),

(2, 1, today(), '29cm', 1.5, 45, 200, '{"total": 45, "products": []}',
 0.78, 0.75, 0.70, 0.85, 'LLM-gpt-4o', '{"model": "gpt-4o", "provider": "openai", "evaluation_type": "screenshot_only"}',
 '검색 결과 양호함', '정확도 보통', '재현율 보통', '[{"goods_no": "124", "goods_name": "테스트상품2", "reason": "관련성 낮음"}]',
 0.78, 0.75, 0.70, 0.77, '검색 결과 양호함', 0.85,
 '/screenshots/test_2.png', 1156, 'high', 3.2, 'test_batch_001', 0, '', now()),

(3, 2, today(), 'musinsa', 1.1, 60, 200, '{"total": 60, "products": []}',
 0.92, 0.88, 0.85, 0.95, 'Composite', '{"individual_results": {"rule_based": {"ndcg_10": 0.90}, "llm": {"ndcg_10": 0.94}}, "weighting_strategy": "confidence_weighted"}',
 '매우 우수한 검색 결과', '정확도 매우 높음', '재현율 우수', '[]',
 0.92, 0.88, 0.85, 0.90, '매우 우수한 검색 결과', 0.95,
 '/screenshots/test_3.png', 1200, 'high', 2.8, 'test_batch_001', 0, '', now()),

-- 어제 데이터
(4, 1, today() - INTERVAL 1 DAY, 'musinsa', 1.3, 48, 200, '{"total": 48, "products": []}',
 0.82, 0.78, 0.73, 0.80, '검색 결과 양호함', 0.88,
 '/screenshots/test_4.png', 1024, 'high', 3.8, 'test_batch_002', 0, '', now()),

(5, 2, today() - INTERVAL 1 DAY, 'musinsa', 1.0, 55, 200, '{"total": 55, "products": []}',
 0.89, 0.85, 0.82, 0.87, '우수한 검색 결과', 0.92,
 '/screenshots/test_5.png', 1180, 'high', 2.9, 'test_batch_002', 0, '', now()),

-- 일주일 전 데이터
(6, 1, today() - INTERVAL 7 DAY, 'musinsa', 1.4, 52, 200, '{"total": 52, "products": []}',
 0.79, 0.76, 0.71, 0.78, '평균적인 검색 결과', 0.83,
 '/screenshots/test_6.png', 1098, 'medium', 4.1, 'test_batch_003', 0, '', now()),

-- 에러 케이스
(7, 3, today(), 'musinsa', 0.0, 0, 500, '{}',
 0.0, 0.0, 0.0, 0.0, '', 0.0,
 '', 0, 'error', 0.5, 'test_batch_001', 3, 'API 호출 실패', now()),

-- 이상치 데이터 (갑작스런 성능 저하)
(8, 10, today(), 'musinsa', 5.2, 10, 200, '{"total": 10, "products": []}',
 0.35, 0.30, 0.25, 0.32, '검색 결과 품질이 매우 낮음', 0.40,
 '/screenshots/test_8.png', 512, 'low', 8.5, 'test_batch_001', 1, '', now()),

-- 고성능 데이터
(9, 7, today(), 'musinsa', 0.8, 80, 200, '{"total": 80, "products": []}',
 0.98, 0.95, 0.92, 0.96, '완벽한 검색 결과', 0.99,
 '/screenshots/test_9.png', 1400, 'high', 2.1, 'test_batch_001', 0, '', now()),

-- 다양한 플랫폼 데이터
(10, 4, today(), '29cm', 1.6, 35, 200, '{"total": 35, "products": []}',
 0.72, 0.68, 0.65, 0.70, '검색 결과 보통', 0.75,
 '/screenshots/test_10.png', 980, 'medium', 4.0, 'test_batch_001', 0, '', now());

-- 키워드 트렌드 테스트 데이터
INSERT INTO keyword_trends (
    keyword_id, platform, trend_date,
    ndcg_7day_avg, ndcg_30day_avg, precision_7day_avg, precision_30day_avg,
    ndcg_change_rate, precision_change_rate, relevance_change_rate,
    is_anomaly, anomaly_score, anomaly_type,
    data_points_count, confidence_interval, updated_at
) VALUES
(1, 'musinsa', today(), 0.84, 0.82, 0.79, 0.77, 2.5, 1.8, 2.1, 0, 0.1, '', 7, 0.95, now()),
(1, '29cm', today(), 0.76, 0.74, 0.73, 0.71, 1.2, 0.8, 1.0, 0, 0.2, '', 7, 0.92, now()),
(2, 'musinsa', today(), 0.91, 0.89, 0.87, 0.85, 1.8, 2.2, 1.9, 0, 0.05, '', 7, 0.98, now()),
(10, 'musinsa', today(), 0.45, 0.72, 0.38, 0.68, -15.2, -18.5, -16.8, 1, 0.85, 'drop', 5, 0.78, now()),
(7, 'musinsa', today(), 0.95, 0.92, 0.92, 0.89, 3.8, 4.2, 4.0, 0, 0.02, '', 7, 0.99, now());

-- 배치 작업 테스트 데이터
INSERT INTO batch_jobs (
    batch_id, job_type, status, total_keywords, processed_keywords, failed_keywords,
    scheduled_at, started_at, completed_at, error_message, log_data,
    avg_processing_time, gpt_api_calls, gpt_api_cost, created_at
) VALUES
('test_batch_001', 'daily_assessment', 'completed', 10, 9, 1, 
 now() - INTERVAL 2 HOUR, now() - INTERVAL 2 HOUR, now() - INTERVAL 1 HOUR,
 '', '{"platform": "musinsa", "keywords_processed": 9}', 3.2, 90, 4.5, now()),

('test_batch_002', 'daily_assessment', 'completed', 5, 5, 0,
 now() - INTERVAL 1 DAY, now() - INTERVAL 1 DAY, now() - INTERVAL 23 HOUR,
 '', '{"platform": "musinsa", "keywords_processed": 5}', 2.8, 50, 2.5, now()),

('test_batch_003', 'trend_analysis', 'running', 100, 45, 0,
 now() - INTERVAL 30 MINUTE, now() - INTERVAL 25 MINUTE, NULL,
 '', '{"platform": "all", "progress": "45%"}', 1.5, 450, 22.5, now()),

('test_batch_004', 'anomaly_detection', 'failed', 20, 15, 5,
 now() - INTERVAL 3 HOUR, now() - INTERVAL 3 HOUR, now() - INTERVAL 2 HOUR,
 'Connection timeout', '{"error_count": 5}', 0.0, 0, 0.0, now());

-- 시스템 메트릭 테스트 데이터
INSERT INTO system_metrics (
    metric_time, metric_type, metric_value, metric_unit,
    component, environment, created_at
) VALUES
(now() - INTERVAL 5 MINUTE, 'cpu', 45.2, 'percent', 'backend', 'test', now()),
(now() - INTERVAL 5 MINUTE, 'memory', 67.8, 'percent', 'backend', 'test', now()),
(now() - INTERVAL 5 MINUTE, 'disk', 23.5, 'percent', 'backend', 'test', now()),
(now() - INTERVAL 5 MINUTE, 'api_latency', 1.2, 'seconds', 'backend', 'test', now()),
(now() - INTERVAL 10 MINUTE, 'cpu', 52.1, 'percent', 'celery', 'test', now()),
(now() - INTERVAL 10 MINUTE, 'memory', 71.3, 'percent', 'celery', 'test', now()),
(now() - INTERVAL 15 MINUTE, 'network', 15.6, 'mbps', 'backend', 'test', now());

-- 이미지 메타데이터 테스트 데이터 (가상의 이미지들)
INSERT INTO image_metadata (
    metadata_id, file_path, s3_url, thumbnail_path, keyword, platform,
    image_format, image_width, image_height, file_size, image_hash,
    created_at, additional_metadata, storage_type, optimization_applied, thumbnail_created
) VALUES
('test_img_001', '/screenshots/test_1.png', '', '/screenshots/test_1_thumb.png', 
 '테스트키워드1', 'musinsa', 'PNG', 1280, 1024, 1024000, 'hash_001',
 now(), '{"quality": "high"}', 'local', 1, 1),

('test_img_002', '/screenshots/test_2.png', 'https://s3.bucket/test_2.png', '/screenshots/test_2_thumb.png',
 '테스트키워드1', '29cm', 'PNG', 1280, 1024, 1156000, 'hash_002',
 now(), '{"quality": "high"}', 'local_s3', 1, 1),

('test_img_003', '/screenshots/test_3.png', '', '/screenshots/test_3_thumb.png',
 '테스트키워드2', 'musinsa', 'PNG', 1280, 1024, 1200000, 'hash_003',
 now(), '{"quality": "high"}', 'local', 1, 1);

-- 알림 로그 테스트 데이터
INSERT INTO notification_logs (
    event_id, rule_id, level, title, message, keyword_id, platform,
    channels, data, timestamp, status
) VALUES
('test_notif_001', 'anomaly_detection_high', 'high', '이상치 탐지: 테스트키워드10',
 '키워드 성능이 급격히 저하되었습니다.', 10, 'musinsa',
 '["email", "slack"]', '{"anomaly_score": 0.85}', now(), 'sent'),

('test_notif_002', 'batch_failure_critical', 'critical', '배치 작업 실패',
 '배치 작업 test_batch_004가 실패했습니다.', 0, 'system',
 '["email", "webhook"]', '{"batch_id": "test_batch_004"}', now(), 'sent'),

('test_notif_003', 'daily_summary_low', 'low', '일일 처리 요약',
 '오늘 총 10개 키워드가 처리되었습니다.', 0, 'system',
 '["email"]', '{"total_processed": 10}', now(), 'sent');