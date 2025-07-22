-- 다중 평가 시스템 지원을 위한 quality_assessment_daily 테이블 컬럼 추가
-- 실행일: 2025-07-22
-- 목적: 기존 GPT 평가 결과와 호환성을 유지하면서 다중 평가 시스템 결과 저장

-- 1. 새로운 컬럼들 개별 추가 (ClickHouse는 한 번에 여러 컬럼 추가 불가)
ALTER TABLE quality_assessment_daily ADD COLUMN IF NOT EXISTS ndcg_score Float32 DEFAULT 0.0;
ALTER TABLE quality_assessment_daily ADD COLUMN IF NOT EXISTS precision_score Float32 DEFAULT 0.0;
ALTER TABLE quality_assessment_daily ADD COLUMN IF NOT EXISTS recall_score Float32 DEFAULT 0.0;
ALTER TABLE quality_assessment_daily ADD COLUMN IF NOT EXISTS confidence_score Float32 DEFAULT 0.0;
ALTER TABLE quality_assessment_daily ADD COLUMN IF NOT EXISTS evaluation_method String DEFAULT 'unknown';
ALTER TABLE quality_assessment_daily ADD COLUMN IF NOT EXISTS evaluation_details String DEFAULT '{}';
ALTER TABLE quality_assessment_daily ADD COLUMN IF NOT EXISTS ndcg_reason String DEFAULT '';
ALTER TABLE quality_assessment_daily ADD COLUMN IF NOT EXISTS precision_reason String DEFAULT '';
ALTER TABLE quality_assessment_daily ADD COLUMN IF NOT EXISTS recall_reason String DEFAULT '';
ALTER TABLE quality_assessment_daily ADD COLUMN IF NOT EXISTS precision_issues String DEFAULT '[]';

-- 2. 기존 데이터 마이그레이션 (GPT 결과를 새 컬럼으로 복사)
UPDATE quality_assessment_daily 
SET 
    ndcg_score = gpt_ndcg_score,
    precision_score = gpt_precision,
    recall_score = gpt_recall,
    confidence_score = gpt_confidence_score,
    evaluation_method = 'LLM-gpt-4o',
    evaluation_details = '{"model": "gpt-4o", "provider": "openai"}'
WHERE ndcg_score = 0.0 AND gpt_ndcg_score > 0.0;

-- 3. 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_quality_assessment_evaluation_method 
ON quality_assessment_daily (evaluation_method) TYPE bloom_filter(0.01);

CREATE INDEX IF NOT EXISTS idx_quality_assessment_confidence 
ON quality_assessment_daily (confidence_score) TYPE minmax; 