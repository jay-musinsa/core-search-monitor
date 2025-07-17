#!/usr/bin/env python3
"""
배치 처리 작업
대용량 키워드 배치 처리 및 관리
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
import time

from celery import group, chain, chord
from celery.result import AsyncResult
from app.core.celery_app import app
from app.tasks.keyword_assessment import assess_single_keyword
import clickhouse_connect
import redis

# 로깅 설정
logger = logging.getLogger(__name__)

@app.task(bind=True, name='process_batch_keywords')
def process_batch_keywords(self, keywords: List[str], platform: str = 'musinsa', 
                          batch_size: int = 10, priority: int = 1) -> Dict:
    """
    대용량 키워드 배치 처리 작업
    
    Args:
        keywords: 처리할 키워드 목록
        platform: 플랫폼 (musinsa, 29cm)
        batch_size: 배치 크기 (동시 처리 수)
        priority: 우선순위 (1-3)
    
    Returns:
        Dict: 배치 처리 결과
    """
    try:
        # 배치 ID 생성
        batch_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        logger.info(f"Starting batch processing: {batch_id}, "
                   f"keywords: {len(keywords)}, platform: {platform}")
        
        # 배치 작업 상태 초기화
        app.batch_job_status.create_job(batch_id, len(keywords))
        
        # 배치 작업 데이터베이스 레코드 생성
        clickhouse_client = clickhouse_connect.get_client(
            host='localhost', port=8123, username='default', password=''
        )
        
        batch_record = [(
            batch_id,
            'daily_assessment',
            'running',
            len(keywords),
            0,  # processed_keywords
            0,  # failed_keywords
            start_time,
            start_time,
            None,  # completed_at
            '',  # error_message
            f'Processing {len(keywords)} keywords on {platform}',
            0.0,  # avg_processing_time
            0,  # gpt_api_calls
            0.0  # gpt_api_cost
        )]
        
        clickhouse_client.insert(
            'batch_jobs',
            batch_record,
            column_names=[
                'batch_id', 'job_type', 'status', 'total_keywords',
                'processed_keywords', 'failed_keywords', 'scheduled_at',
                'started_at', 'completed_at', 'error_message', 'log_data',
                'avg_processing_time', 'gpt_api_calls', 'gpt_api_cost'
            ]
        )
        
        # 키워드를 배치로 분할
        keyword_batches = [
            keywords[i:i + batch_size] 
            for i in range(0, len(keywords), batch_size)
        ]
        
        # 각 배치를 병렬로 처리
        all_results = []
        failed_keywords = []
        
        for batch_idx, keyword_batch in enumerate(keyword_batches):
            logger.info(f"Processing batch {batch_idx + 1}/{len(keyword_batches)}")
            
            # 배치 내 키워드들을 병렬로 처리
            batch_tasks = []
            for keyword in keyword_batch:
                task = assess_single_keyword.apply_async(
                    args=[keyword, platform],
                    kwargs={'batch_id': batch_id, 'priority': priority}
                )
                batch_tasks.append((keyword, task))
            
            # 배치 완료 대기
            batch_results = []
            for keyword, task in batch_tasks:
                try:
                    # 작업 완료 대기 (타임아웃 30분)
                    result = task.get(timeout=1800)
                    batch_results.append(result)
                    all_results.append(result)
                    
                    logger.info(f"Keyword '{keyword}' processed successfully")
                    
                except Exception as e:
                    logger.error(f"Keyword '{keyword}' failed: {e}")
                    failed_keywords.append({'keyword': keyword, 'error': str(e)})
                    
                    # 실패 결과 기록
                    batch_results.append({
                        'keyword': keyword,
                        'platform': platform,
                        'status': 'failed',
                        'error': str(e),
                        'batch_id': batch_id
                    })
            
            # 배치 간 간격 (API 레이트 리밋 방지)
            if batch_idx < len(keyword_batches) - 1:
                time.sleep(2)
        
        # 완료 시간 및 통계 계산
        end_time = datetime.now()
        total_processing_time = (end_time - start_time).total_seconds()
        
        # 성공/실패 통계
        successful_count = len(all_results) - len(failed_keywords)
        failed_count = len(failed_keywords)
        
        # 평균 처리 시간 계산
        processing_times = [
            r.get('processing_time', 0) 
            for r in all_results 
            if r.get('processing_time')
        ]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        # GPT API 사용량 추정 (키워드당 1회 호출)
        gpt_api_calls = successful_count
        gpt_api_cost = gpt_api_calls * 0.01  # 대략적인 비용 추정
        
        # 배치 작업 상태 업데이트
        app.batch_job_status.update_job(
            batch_id,
            status='completed',
            processed_keywords=successful_count,
            failed_keywords=failed_count,
            completed_at=end_time.timestamp()
        )
        
        # 데이터베이스 레코드 업데이트
        clickhouse_client.query(f"""
            ALTER TABLE batch_jobs 
            UPDATE 
                status = 'completed',
                processed_keywords = {successful_count},
                failed_keywords = {failed_count},
                completed_at = '{end_time.isoformat()}',
                avg_processing_time = {avg_processing_time},
                gpt_api_calls = {gpt_api_calls},
                gpt_api_cost = {gpt_api_cost},
                log_data = '{json.dumps({"total_time": total_processing_time, "avg_time": avg_processing_time}, ensure_ascii=False)}'
            WHERE batch_id = '{batch_id}'
        """)
        
        result = {
            'batch_id': batch_id,
            'status': 'completed',
            'total_keywords': len(keywords),
            'successful_count': successful_count,
            'failed_count': failed_count,
            'total_processing_time': total_processing_time,
            'avg_processing_time': avg_processing_time,
            'gpt_api_calls': gpt_api_calls,
            'gpt_api_cost': gpt_api_cost,
            'results': all_results,
            'failed_keywords': failed_keywords,
            'started_at': start_time.isoformat(),
            'completed_at': end_time.isoformat()
        }
        
        logger.info(f"Batch processing completed: {batch_id}, "
                   f"success: {successful_count}, failed: {failed_count}")
        
        return result
        
    except Exception as exc:
        logger.error(f"Error in process_batch_keywords: {exc}")
        
        # 배치 작업 실패 상태 업데이트
        app.batch_job_status.update_job(
            batch_id,
            status='failed',
            error_message=str(exc),
            completed_at=datetime.now().timestamp()
        )
        
        # 데이터베이스 레코드 업데이트
        try:
            clickhouse_client.query(f"""
                ALTER TABLE batch_jobs 
                UPDATE 
                    status = 'failed',
                    error_message = '{str(exc)}',
                    completed_at = '{datetime.now().isoformat()}'
                WHERE batch_id = '{batch_id}'
            """)
        except:
            pass
        
        raise exc

@app.task(bind=True, name='daily_keyword_assessment')
def daily_keyword_assessment(self, assessment_date: Optional[str] = None) -> Dict:
    """
    일일 키워드 품질 평가 작업
    
    Args:
        assessment_date: 평가 일자 (YYYY-MM-DD 형식, 기본값: 오늘)
    
    Returns:
        Dict: 일일 평가 결과
    """
    try:
        # 평가 일자 설정
        if assessment_date:
            target_date = datetime.strptime(assessment_date, '%Y-%m-%d').date()
        else:
            target_date = date.today()
        
        logger.info(f"Starting daily keyword assessment for {target_date}")
        
        # 활성 키워드 조회
        clickhouse_client = clickhouse_connect.get_client(
            host='localhost', port=8123, username='default', password=''
        )
        
        result = clickhouse_client.query("""
            SELECT keyword, priority 
            FROM keyword_master 
            WHERE is_active = 1 
            ORDER BY priority ASC, keyword ASC
        """)
        
        keywords_data = result.result_rows
        
        if not keywords_data:
            logger.warning("No active keywords found for assessment")
            return {
                'status': 'completed',
                'message': 'No active keywords found',
                'total_keywords': 0
            }
        
        # 키워드 목록 생성
        keywords = [row[0] for row in keywords_data]
        
        logger.info(f"Found {len(keywords)} active keywords for assessment")
        
        # 플랫폼별 배치 처리
        platforms = ['musinsa']  # 29cm은 추후 추가
        batch_results = []
        
        for platform in platforms:
            logger.info(f"Processing keywords for platform: {platform}")
            
            # 배치 처리 실행
            batch_task = process_batch_keywords.apply_async(
                args=[keywords, platform],
                kwargs={'batch_size': 5, 'priority': 1}  # 일일 평가는 배치 크기 5
            )
            
            try:
                # 배치 완료 대기 (최대 2시간)
                batch_result = batch_task.get(timeout=7200)
                batch_results.append(batch_result)
                
                logger.info(f"Platform {platform} batch completed: "
                           f"success={batch_result['successful_count']}, "
                           f"failed={batch_result['failed_count']}")
                
            except Exception as e:
                logger.error(f"Platform {platform} batch failed: {e}")
                batch_results.append({
                    'platform': platform,
                    'status': 'failed',
                    'error': str(e)
                })
        
        # 전체 결과 집계
        total_successful = sum(r.get('successful_count', 0) for r in batch_results)
        total_failed = sum(r.get('failed_count', 0) for r in batch_results)
        total_gpt_calls = sum(r.get('gpt_api_calls', 0) for r in batch_results)
        total_gpt_cost = sum(r.get('gpt_api_cost', 0) for r in batch_results)
        
        result = {
            'status': 'completed',
            'assessment_date': target_date.isoformat(),
            'total_keywords': len(keywords),
            'platforms_processed': len(platforms),
            'total_successful': total_successful,
            'total_failed': total_failed,
            'total_gpt_calls': total_gpt_calls,
            'total_gpt_cost': total_gpt_cost,
            'batch_results': batch_results,
            'completed_at': datetime.now().isoformat()
        }
        
        logger.info(f"Daily keyword assessment completed: "
                   f"success={total_successful}, failed={total_failed}")
        
        return result
        
    except Exception as exc:
        logger.error(f"Error in daily_keyword_assessment: {exc}")
        raise exc

@app.task(bind=True, name='get_batch_status')
def get_batch_status(self, batch_id: str) -> Dict:
    """
    배치 작업 상태 조회
    
    Args:
        batch_id: 배치 작업 ID
    
    Returns:
        Dict: 배치 상태 정보
    """
    try:
        # Redis에서 실시간 상태 조회
        redis_status = app.batch_job_status.get_job(batch_id)
        
        # ClickHouse에서 세부 정보 조회
        clickhouse_client = clickhouse_connect.get_client(
            host='localhost', port=8123, username='default', password=''
        )
        
        result = clickhouse_client.query(
            "SELECT * FROM batch_jobs WHERE batch_id = %(batch_id)s",
            {'batch_id': batch_id}
        )
        
        if result.result_rows:
            db_data = result.result_rows[0]
            column_names = [col.name for col in result.column_names]
            db_status = dict(zip(column_names, db_data))
        else:
            db_status = {}
        
        # 결과 병합
        combined_status = {
            'batch_id': batch_id,
            'status': redis_status.get('status', db_status.get('status', 'unknown')),
            'total_keywords': int(redis_status.get('total_keywords', db_status.get('total_keywords', 0))),
            'processed_keywords': int(redis_status.get('processed_keywords', db_status.get('processed_keywords', 0))),
            'failed_keywords': int(redis_status.get('failed_keywords', db_status.get('failed_keywords', 0))),
            'progress_percentage': 0,
            'estimated_completion': None,
            'db_info': db_status,
            'redis_info': redis_status
        }
        
        # 진행률 계산
        if combined_status['total_keywords'] > 0:
            combined_status['progress_percentage'] = (
                (combined_status['processed_keywords'] + combined_status['failed_keywords']) /
                combined_status['total_keywords'] * 100
            )
        
        return combined_status
        
    except Exception as exc:
        logger.error(f"Error in get_batch_status: {exc}")
        return {
            'batch_id': batch_id,
            'status': 'error',
            'error': str(exc)
        }

@app.task(bind=True, name='cleanup_old_batches')
def cleanup_old_batches(self, days_old: int = 7) -> Dict:
    """
    오래된 배치 작업 정리
    
    Args:
        days_old: 삭제할 배치 작업 기준 일수
    
    Returns:
        Dict: 정리 결과
    """
    try:
        # ClickHouse에서 오래된 배치 작업 조회
        clickhouse_client = clickhouse_connect.get_client(
            host='localhost', port=8123, username='default', password=''
        )
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        # 오래된 배치 작업 조회
        result = clickhouse_client.query(f"""
            SELECT batch_id, status, created_at 
            FROM batch_jobs 
            WHERE created_at < '{cutoff_date.isoformat()}'
            AND status IN ('completed', 'failed')
        """)
        
        old_batches = result.result_rows
        
        if not old_batches:
            logger.info("No old batches found for cleanup")
            return {
                'status': 'completed',
                'cleaned_batches': 0,
                'message': 'No old batches found'
            }
        
        # Redis에서 배치 상태 정보 삭제
        redis_client = redis.Redis.from_url(app.conf.broker_url)
        cleaned_count = 0
        
        for batch_id, status, created_at in old_batches:
            try:
                # Redis에서 삭제
                redis_key = f"batch_job:{batch_id}"
                redis_client.delete(redis_key)
                cleaned_count += 1
                
                logger.info(f"Cleaned batch: {batch_id} (status: {status})")
                
            except Exception as e:
                logger.error(f"Error cleaning batch {batch_id}: {e}")
        
        logger.info(f"Cleaned {cleaned_count} old batches")
        
        return {
            'status': 'completed',
            'cleaned_batches': cleaned_count,
            'total_old_batches': len(old_batches),
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error in cleanup_old_batches: {exc}")
        return {
            'status': 'error',
            'error': str(exc)
        }

# 편의 함수들
def start_batch_processing(keywords: List[str], platform: str = 'musinsa') -> str:
    """배치 처리 시작"""
    task = process_batch_keywords.delay(keywords, platform)
    return task.id

def start_daily_assessment(assessment_date: Optional[str] = None) -> str:
    """일일 평가 시작"""
    task = daily_keyword_assessment.delay(assessment_date)
    return task.id

def check_batch_status(batch_id: str) -> Dict:
    """배치 상태 확인"""
    task = get_batch_status.delay(batch_id)
    return task.get(timeout=30)