#!/usr/bin/env python3
"""
키워드 품질 평가 작업
개별 키워드에 대한 품질 평가 및 결과 저장
"""

import asyncio
import logging
from datetime import datetime, date
from typing import Dict, List, Optional
import json
import traceback
import uuid

from celery import Task
from app.core.celery_app import app
from app.core.crawler import CrawlerMusinsa, Crawler29CM
from app.core.gpt import GPTMetricEvaluator
from app.core.musinsa_api_service import MusinsaAPIService
import clickhouse_connect
import redis

# 로깅 설정
logger = logging.getLogger(__name__)

class KeywordAssessmentTask(Task):
    """키워드 품질 평가 작업 기본 클래스"""
    
    def __init__(self):
        # Task 클래스는 기본적으로 인자 없는 __init__을 지원하지 않을 수 있음
        # 대신 속성만 초기화
        self.clickhouse_client = None
        self.redis_client = None
        self.crawler = None
        self.gpt_evaluator = None
        self.api_service = None
    
    def setup_connections(self):
        """연결 설정"""
        if not self.clickhouse_client:
            self.clickhouse_client = clickhouse_connect.get_client(
                host='localhost',
                port=8123,
                username='default',
                password=''
            )
        
        if not self.redis_client:
            self.redis_client = redis.Redis.from_url(app.conf.broker_url)
        
        if not self.crawler:
            self.crawler = CrawlerMusinsa()
        
        if not self.gpt_evaluator:
            self.gpt_evaluator = GPTMetricEvaluator()
        
        if not self.api_service:
            self.api_service = MusinsaAPIService()
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """작업 실패 시 처리"""
        logger.error(f"Task {task_id} failed: {exc}")
        logger.error(f"Exception info: {einfo}")
        
        # 배치 작업 실패 카운트 증가
        if 'batch_id' in kwargs:
            batch_id = kwargs['batch_id']
            app.batch_job_status.increment_failed(batch_id)
    
    def on_success(self, retval, task_id, args, kwargs):
        """작업 성공 시 처리"""
        logger.info(f"Task {task_id} completed successfully")
        
        # 배치 작업 성공 카운트 증가
        if 'batch_id' in kwargs:
            batch_id = kwargs['batch_id']
            app.batch_job_status.increment_processed(batch_id)

@app.task(name='assess_single_keyword')
def assess_single_keyword(keyword: str, platform: str = 'musinsa', 
                         batch_id: Optional[str] = None, priority: int = 1):
    """
    단일 키워드 품질 평가 작업 (실제 core 서비스 사용)
    
    Args:
        keyword: 평가할 키워드
        platform: 플랫폼 (musinsa, 29cm)
        batch_id: 배치 작업 ID (선택사항)
        priority: 우선순위 (1-3)
    
    Returns:
        Dict: 평가 결과
    """
    try:
        # 시작 시간
        start_time = datetime.now()
        assessment_id = str(uuid.uuid4())
        
        logger.info(f"Starting assessment for keyword: {keyword} on {platform}")
        
        # metrics_manager를 통한 통합 처리 (비동기 함수를 동기로 실행)
        import asyncio
        from app.core.metrics import metrics_manager
        
        # 새 이벤트 루프 생성 또는 기존 루프 사용
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # metrics_manager로 실제 core 서비스들을 사용한 평가 수행
        evaluation_result = loop.run_until_complete(
            metrics_manager.process_keyword(keyword)
        )
        
        # 에러 처리
        if "error" in evaluation_result:
            logger.error(f"MetricsManager failed for {keyword}: {evaluation_result['error']}")
            raise Exception(evaluation_result["error"])
        
        # 1. 키워드 ID 조회 또는 생성 (ClickHouse)
        keyword_id = get_or_create_keyword_id(keyword, priority)
        
        # 2. 무신사/29cm 결과에서 주요 메트릭 추출
        musinsa_result = evaluation_result.get('musinsa', {})
        cm29_result = evaluation_result.get('29cm', {})
        
        # 플랫폼에 따른 결과 선택 (기본적으로 무신사 우선)
        if platform == '29cm' and cm29_result:
            primary_result = cm29_result
            primary_platform = '29cm'
        else:
            primary_result = musinsa_result
            primary_platform = 'musinsa'
        
        # 3. 결과 저장 (ClickHouse quality_assessment_daily 테이블)
        save_assessment_result_to_db(
            assessment_id, keyword_id, keyword, primary_platform, 
            primary_result, start_time, batch_id
        )
        
        # 처리 시간 계산
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Assessment completed for keyword: {keyword}, "
                   f"processing time: {processing_time:.2f}s")
        
        # Celery task 표준 형식으로 결과 반환
        return {
            'assessment_id': assessment_id,
            'keyword': keyword,
            'platform': primary_platform,
            'status': 'completed',
            'processing_time': processing_time,
            'gpt_scores': {
                'ndcg_score': primary_result.get('ndcg@10', 0),
                'precision': primary_result.get('precision', 0),
                'recall': primary_result.get('recall', 0)
            },
                         'api_results': estimate_api_results_count(evaluation_result),
            'screenshot_path': primary_result.get('screenshot', ''),
            'batch_id': batch_id,
            # 추가 상세 정보
            'evaluation_details': {
                'musinsa': musinsa_result,
                '29cm': cm29_result,
                'ndcg_reason': primary_result.get('ndcg_reason', ''),
                'precision_reason': primary_result.get('precision_reason', ''),
                'recall_reason': primary_result.get('recall_reason', ''),
                'precision_issues': primary_result.get('precision_issues', [])
            }
        }
        
    except Exception as exc:
        logger.error(f"Error in assess_single_keyword: {exc}")
        import traceback
        logger.error(traceback.format_exc())
        raise exc

# 헬퍼 함수들

def get_or_create_keyword_id(keyword: str, priority: int = 1) -> int:
    """키워드 ID 조회 또는 생성"""
    try:
        # ClickHouse 연결
        import clickhouse_connect
        clickhouse_client = clickhouse_connect.get_client(
            host='localhost', port=8123, username='default', password=''
        )
        
        # 기존 키워드 조회
        result = clickhouse_client.query(
            "SELECT id FROM keyword_master WHERE keyword = %(keyword)s",
            {'keyword': keyword}
        )
        
        if result.result_rows:
            return result.result_rows[0][0]
        
        # 새 키워드 생성
        max_id_result = clickhouse_client.query("SELECT max(id) FROM keyword_master")
        new_id = (max_id_result.result_rows[0][0] or 0) + 1
        
        # 카테고리 자동 분류
        category = 'general'
        if any(word in keyword for word in ['스니커즈', '운동화', '구두', '부츠', '신발']):
            category = 'shoes'
        elif any(word in keyword for word in ['바지', '청바지', '원피스', '셔츠', '티셔츠', '후드티']):
            category = 'clothing'
        elif any(word in keyword for word in ['가방', '백팩', '지갑', '벨트']):
            category = 'accessories'
        
        # 키워드 삽입
        clickhouse_client.insert(
            'keyword_master',
            [(new_id, keyword, category, priority, True, datetime.now())],
            column_names=['id', 'keyword', 'category', 'priority', 'is_active', 'created_at']
        )
        
        logger.info(f"Created new keyword: {keyword} with ID: {new_id}")
        return new_id
        
    except Exception as e:
        logger.error(f"Error in get_or_create_keyword_id: {e}")
        return 1


def estimate_api_results_count(evaluation_result: Dict) -> int:
    """평가 결과에서 API 결과 수를 추정"""
    try:
        # 무신사 결과에서 precision_issues 개수로 추정
        musinsa_result = evaluation_result.get('musinsa', {})
        precision_issues = musinsa_result.get('precision_issues', [])
        if precision_issues:
            return len(precision_issues)
        
        # precision_issues가 없으면 기본값 반환
        return 10  # 일반적으로 검색 결과 10-50개
    except Exception as e:
        logger.error(f"Error estimating API results count: {e}")
        return 0


def save_assessment_result_to_db(assessment_id: str, keyword_id: int, keyword: str,
                                platform: str, evaluation_result: Dict, 
                                start_time: datetime, batch_id: Optional[str]):
    """평가 결과를 ClickHouse에 저장"""
    try:
        # ClickHouse 연결
        import clickhouse_connect
        clickhouse_client = clickhouse_connect.get_client(
            host='localhost', port=8123, username='default', password=''
        )
        
        # 현재 시간
        now = datetime.now()
        assessment_date = now.date()
        processing_time = (now - start_time).total_seconds()
        
        # 평가 결과에서 데이터 추출
        ndcg_score = evaluation_result.get('ndcg@10', 0.0)
        precision = evaluation_result.get('precision', 0.0)
        recall = evaluation_result.get('recall', 0.0)
        screenshot_path = evaluation_result.get('screenshot', '')
        ndcg_reason = evaluation_result.get('ndcg_reason', '')
        precision_reason = evaluation_result.get('precision_reason', '')
        recall_reason = evaluation_result.get('recall_reason', '')
        
        # 스크린샷 정보
        screenshot_size = 0
        screenshot_quality = 'none'
        if screenshot_path:
            try:
                import os
                if screenshot_path.startswith('/screenshot/'):
                    abs_path = os.path.join(os.path.dirname(__file__), '..', screenshot_path.lstrip('/'))
                    if os.path.exists(abs_path):
                        screenshot_size = os.path.getsize(abs_path)
                        screenshot_quality = 'high'
            except Exception:
                pass
        
        # 데이터 삽입 시도 (테이블이 존재하지 않으면 건너뜀)
        try:
            assessment_data = [(
                hash(assessment_id),  # id를 hash로 변환
                keyword_id,
                assessment_date,
                platform,
                
                # API 응답 메트릭스 (기본값)
                0.5,  # api_response_time
                0,    # api_total_results
                200,  # api_status_code
                json.dumps({'processed_by': 'metrics_manager'}, ensure_ascii=False),  # api_response_data
                
                # GPT 평가 결과
                ndcg_score,
                precision,
                recall,
                0.0,  # gpt_relevance_score (기본값)
                f"{ndcg_reason} | {precision_reason} | {recall_reason}",  # gpt_evaluation_text
                0.8,  # gpt_confidence_score (기본값)
                
                # 스크린샷 정보
                screenshot_path,
                screenshot_size,
                screenshot_quality,
                
                # 처리 메타데이터
                processing_time,
                batch_id or '',
                0,  # retry_count
                '',  # error_message
                now
            )]
            
            clickhouse_client.insert(
                'quality_assessment_daily',
                assessment_data,
                column_names=[
                    'id', 'keyword_id', 'assessment_date', 'platform',
                    'api_response_time', 'api_total_results', 'api_status_code', 'api_response_data',
                    'gpt_ndcg_score', 'gpt_precision', 'gpt_recall', 'gpt_relevance_score',
                    'gpt_evaluation_text', 'gpt_confidence_score',
                    'screenshot_path', 'screenshot_size', 'screenshot_quality',
                    'processing_time', 'batch_id', 'retry_count', 'error_message', 'created_at'
                ]
            )
            
            logger.info(f"Assessment result saved to ClickHouse for keyword: {keyword}")
            
        except Exception as db_error:
            logger.warning(f"Could not save to ClickHouse (table may not exist): {db_error}")
            # 데이터베이스 저장 실패해도 평가는 계속 진행
        
    except Exception as e:
        logger.error(f"Error in save_assessment_result_to_db: {e}")
        # 저장 실패해도 평가 자체는 성공으로 처리


# 편의 함수들

def assess_keyword_async(keyword: str, platform: str = 'musinsa', priority: int = 1) -> str:
    """키워드 평가 작업 비동기 실행"""
    task = assess_single_keyword.delay(keyword, platform, priority=priority)
    return task.id