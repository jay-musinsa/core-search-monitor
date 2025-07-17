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

@app.task(bind=True, base=KeywordAssessmentTask, name='assess_single_keyword', 
          max_retries=3, default_retry_delay=60)
def assess_single_keyword(self, keyword: str, platform: str = 'musinsa', 
                         batch_id: Optional[str] = None, priority: int = 1):
    """
    단일 키워드 품질 평가 작업
    
    Args:
        keyword: 평가할 키워드
        platform: 플랫폼 (musinsa, 29cm)
        batch_id: 배치 작업 ID (선택사항)
        priority: 우선순위 (1-3)
    
    Returns:
        Dict: 평가 결과
    """
    try:
        # 연결 설정
        self.setup_connections()
        
        # 작업 시작 시간
        start_time = datetime.now()
        
        # 고유 ID 생성
        assessment_id = str(uuid.uuid4())
        
        logger.info(f"Starting assessment for keyword: {keyword} on {platform}")
        
        # 1. 키워드 마스터에서 키워드 ID 조회 또는 생성
        keyword_id = self._get_or_create_keyword_id(keyword, priority)
        
        # 2. API 데이터 수집
        api_data = self._collect_api_data(keyword, platform)
        
        # 3. 스크린샷 생성
        screenshot_data = self._capture_screenshot(keyword, platform)
        
        # 4. GPT 평가 수행
        gpt_evaluation = self._perform_gpt_evaluation(
            keyword, api_data, screenshot_data, platform
        )
        
        # 5. 결과 저장
        assessment_result = self._save_assessment_result(
            assessment_id, keyword_id, keyword, platform, api_data, 
            screenshot_data, gpt_evaluation, start_time, batch_id
        )
        
        # 6. 처리 시간 계산
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Assessment completed for keyword: {keyword}, "
                   f"processing time: {processing_time:.2f}s")
        
        return {
            'assessment_id': assessment_id,
            'keyword': keyword,
            'platform': platform,
            'status': 'completed',
            'processing_time': processing_time,
            'gpt_scores': {
                'ndcg_score': gpt_evaluation.get('ndcg_score', 0),
                'precision': gpt_evaluation.get('precision', 0),
                'recall': gpt_evaluation.get('recall', 0)
            },
            'api_results': api_data.get('total_results', 0),
            'screenshot_path': screenshot_data.get('path', ''),
            'batch_id': batch_id
        }
        
    except Exception as exc:
        logger.error(f"Error in assess_single_keyword: {exc}")
        logger.error(traceback.format_exc())
        
        # 재시도 로직
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task, attempt {self.request.retries + 1}")
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
        
        # 최대 재시도 횟수 초과 시 에러 결과 저장
        self._save_error_result(keyword, platform, str(exc), batch_id)
        raise exc

    def _get_or_create_keyword_id(self, keyword: str, priority: int) -> int:
        """키워드 ID 조회 또는 생성"""
        try:
            # 기존 키워드 조회
            result = self.clickhouse_client.query(
                "SELECT id FROM keyword_master WHERE keyword = %(keyword)s",
                {'keyword': keyword}
            )
            
            if result.result_rows:
                return result.result_rows[0][0]
            
            # 새 키워드 생성
            # 새 ID 생성 (max ID + 1)
            max_id_result = self.clickhouse_client.query(
                "SELECT max(id) FROM keyword_master"
            )
            new_id = (max_id_result.result_rows[0][0] or 0) + 1
            
            # 카테고리 자동 분류 (간단한 로직)
            category = self._classify_keyword_category(keyword)
            
            # 키워드 삽입
            self.clickhouse_client.insert(
                'keyword_master',
                [(new_id, keyword, category, priority)],
                column_names=['id', 'keyword', 'category', 'priority']
            )
            
            logger.info(f"Created new keyword: {keyword} with ID: {new_id}")
            return new_id
            
        except Exception as e:
            logger.error(f"Error in _get_or_create_keyword_id: {e}")
            raise

    def _classify_keyword_category(self, keyword: str) -> str:
        """키워드 카테고리 자동 분류"""
        clothing_keywords = ['원피스', '바지', '청바지', '셔츠', '후드티', '니트', '코트', '자켓']
        shoes_keywords = ['운동화', '스니커즈', '구두', '부츠', '슬리퍼', '샌들']
        bags_keywords = ['가방', '백팩', '크로스백', '토트백', '클러치']
        accessories_keywords = ['시계', '반지', '목걸이', '귀걸이', '모자', '벨트']
        
        keyword_lower = keyword.lower()
        
        for word in clothing_keywords:
            if word in keyword_lower:
                return 'clothing'
        
        for word in shoes_keywords:
            if word in keyword_lower:
                return 'shoes'
        
        for word in bags_keywords:
            if word in keyword_lower:
                return 'bags'
        
        for word in accessories_keywords:
            if word in keyword_lower:
                return 'accessories'
        
        return 'other'

    def _collect_api_data(self, keyword: str, platform: str) -> Dict:
        """API 데이터 수집"""
        try:
            start_time = datetime.now()
            
            if platform == 'musinsa':
                # 무신사 API 호출
                api_results = self.api_service.fetch_search_data(keyword, size=50)
            else:
                # 29cm API는 아직 구현되지 않음
                api_results = {'products': [], 'total': 0}
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            # 무신사 API 응답 구조에 맞게 수정
            products_list = []
            if api_results and 'data' in api_results and 'list' in api_results['data']:
                products_list = api_results['data']['list']
            
            return {
                'response_time': response_time,
                'total_results': len(products_list),
                'status_code': 200,
                'data': json.dumps(api_results, ensure_ascii=False)
            }
            
        except Exception as e:
            logger.error(f"Error in _collect_api_data: {e}")
            return {
                'response_time': 0,
                'total_results': 0,
                'status_code': 500,
                'data': json.dumps({'error': str(e)}, ensure_ascii=False)
            }

    def _capture_screenshot(self, keyword: str, platform: str) -> Dict:
        """스크린샷 캡처"""
        try:
            if platform == 'musinsa':
                screenshot_path = self.crawler.capture_screenshot(keyword)
            else:
                # 29cm 스크린샷은 아직 구현되지 않음
                screenshot_path = None
            
            if screenshot_path:
                import os
                file_size = os.path.getsize(screenshot_path)
                return {
                    'path': screenshot_path,
                    'size': file_size,
                    'quality': 'high'
                }
            else:
                return {
                    'path': '',
                    'size': 0,
                    'quality': 'none'
                }
                
        except Exception as e:
            logger.error(f"Error in _capture_screenshot: {e}")
            return {
                'path': '',
                'size': 0,
                'quality': 'error'
            }

    def _perform_gpt_evaluation(self, keyword: str, api_data: Dict, 
                              screenshot_data: Dict, platform: str) -> Dict:
        """GPT 평가 수행"""
        try:
            if screenshot_data['path']:
                # 스크린샷 기반 평가
                evaluation_result = self.gpt_evaluator.evaluate(
                    screenshot_data['path'], keyword
                )
            else:
                # API 데이터 기반 평가 (fallback)
                evaluation_result = self._evaluate_from_api_data(
                    keyword, api_data, platform
                )
            
            return {
                'ndcg_score': evaluation_result.get('ndcg_score', 0),
                'precision': evaluation_result.get('precision', 0),
                'recall': evaluation_result.get('recall', 0),
                'relevance_score': evaluation_result.get('relevance_score', 0),
                'evaluation_text': evaluation_result.get('explanation', ''),
                'confidence_score': evaluation_result.get('confidence', 0)
            }
            
        except Exception as e:
            logger.error(f"Error in _perform_gpt_evaluation: {e}")
            return {
                'ndcg_score': 0,
                'precision': 0,
                'recall': 0,
                'relevance_score': 0,
                'evaluation_text': f'GPT 평가 실패: {str(e)}',
                'confidence_score': 0
            }

    def _evaluate_from_api_data(self, keyword: str, api_data: Dict, platform: str) -> Dict:
        """API 데이터 기반 평가 (fallback)"""
        # 간단한 휴리스틱 평가
        total_results = api_data.get('total_results', 0)
        
        if total_results == 0:
            return {
                'ndcg_score': 0,
                'precision': 0,
                'recall': 0,
                'relevance_score': 0,
                'explanation': 'API 결과 없음',
                'confidence': 0.5
            }
        
        # 결과 수가 많을수록 높은 점수 (간단한 로직)
        score = min(total_results / 50, 1.0)
        
        return {
            'ndcg_score': score,
            'precision': score,
            'recall': score * 0.8,
            'relevance_score': score,
            'explanation': f'API 기반 평가: {total_results}개 결과',
            'confidence': 0.6
        }

    def _save_assessment_result(self, assessment_id: str, keyword_id: int, 
                              keyword: str, platform: str, api_data: Dict,
                              screenshot_data: Dict, gpt_evaluation: Dict,
                              start_time: datetime, batch_id: Optional[str]) -> Dict:
        """평가 결과 저장"""
        try:
            # 현재 시간
            now = datetime.now()
            assessment_date = now.date()
            
            # 처리 시간 계산
            processing_time = (now - start_time).total_seconds()
            
            # 데이터 삽입
            assessment_data = [(
                hash(assessment_id),  # id를 hash로 변환
                keyword_id,
                assessment_date,
                platform,
                
                # API 응답 메트릭스
                api_data.get('response_time', 0),
                api_data.get('total_results', 0),
                api_data.get('status_code', 500),
                api_data.get('data', ''),
                
                # GPT 평가 결과
                gpt_evaluation.get('ndcg_score', 0),
                gpt_evaluation.get('precision', 0),
                gpt_evaluation.get('recall', 0),
                gpt_evaluation.get('relevance_score', 0),
                gpt_evaluation.get('evaluation_text', ''),
                gpt_evaluation.get('confidence_score', 0),
                
                # 스크린샷 정보
                screenshot_data.get('path', ''),
                screenshot_data.get('size', 0),
                screenshot_data.get('quality', 'none'),
                
                # 처리 메타데이터
                processing_time,
                batch_id or '',
                0,  # retry_count
                '',  # error_message
                now
            )]
            
            self.clickhouse_client.insert(
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
            
            logger.info(f"Assessment result saved for keyword: {keyword}")
            
            return {
                'assessment_id': assessment_id,
                'keyword_id': keyword_id,
                'saved_at': now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in _save_assessment_result: {e}")
            raise

    def _save_error_result(self, keyword: str, platform: str, error_message: str, batch_id: Optional[str]):
        """에러 결과 저장"""
        try:
            # 키워드 ID 조회 (에러 상황이므로 생성하지 않음)
            result = self.clickhouse_client.query(
                "SELECT id FROM keyword_master WHERE keyword = %(keyword)s",
                {'keyword': keyword}
            )
            
            keyword_id = result.result_rows[0][0] if result.result_rows else 0
            
            # 에러 데이터 삽입
            error_data = [(
                hash(f"error_{keyword}_{platform}_{datetime.now().timestamp()}"),
                keyword_id,
                date.today(),
                platform,
                0, 0, 500, json.dumps({'error': error_message}, ensure_ascii=False),
                0, 0, 0, 0, f'평가 실패: {error_message}', 0,
                '', 0, 'error',
                0, batch_id or '', 0, error_message, datetime.now()
            )]
            
            self.clickhouse_client.insert(
                'quality_assessment_daily',
                error_data,
                column_names=[
                    'id', 'keyword_id', 'assessment_date', 'platform',
                    'api_response_time', 'api_total_results', 'api_status_code', 'api_response_data',
                    'gpt_ndcg_score', 'gpt_precision', 'gpt_recall', 'gpt_relevance_score',
                    'gpt_evaluation_text', 'gpt_confidence_score',
                    'screenshot_path', 'screenshot_size', 'screenshot_quality',
                    'processing_time', 'batch_id', 'retry_count', 'error_message', 'created_at'
                ]
            )
            
            logger.info(f"Error result saved for keyword: {keyword}")
            
        except Exception as e:
            logger.error(f"Error in _save_error_result: {e}")

# 편의 함수들
def assess_keyword_sync(keyword: str, platform: str = 'musinsa', priority: int = 1) -> str:
    """키워드 평가 작업 동기 실행 (개발/테스트용)"""
    task = assess_single_keyword.apply_async(
        args=[keyword, platform], 
        kwargs={'priority': priority}
    )
    return task.id

def assess_keyword_async(keyword: str, platform: str = 'musinsa', priority: int = 1) -> str:
    """키워드 평가 작업 비동기 실행"""
    task = assess_single_keyword.delay(keyword, platform, priority=priority)
    return task.id