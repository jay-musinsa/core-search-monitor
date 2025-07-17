#!/usr/bin/env python3
"""
Celery 애플리케이션 설정
대용량 키워드 배치 처리를 위한 비동기 작업 큐 시스템
"""

import os
from celery import Celery
from celery.signals import worker_ready, worker_shutdown
from kombu import Queue
import redis
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Celery 애플리케이션 생성
app = Celery('keyword_quality_assessment')

# 설정
app.conf.update(
    # 브로커 설정 (Redis)
    broker_url=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2'),
    
    # 작업 설정
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Seoul',
    enable_utc=True,
    
    # 워커 설정
    worker_prefetch_multiplier=1,  # 메모리 사용량 최적화
    worker_max_tasks_per_child=1000,  # 메모리 누수 방지
    worker_disable_rate_limits=False,
    
    # 큐 설정
    task_routes={
        'keyword_quality_assessment.tasks.assess_single_keyword': {
            'queue': 'keyword_assessment',
            'routing_key': 'keyword_assessment',
        },
        'keyword_quality_assessment.tasks.process_batch_keywords': {
            'queue': 'batch_processing',
            'routing_key': 'batch_processing',
        },
        'keyword_quality_assessment.tasks.analyze_trends': {
            'queue': 'trend_analysis',
            'routing_key': 'trend_analysis',
        },
        'keyword_quality_assessment.tasks.detect_anomalies': {
            'queue': 'anomaly_detection',
            'routing_key': 'anomaly_detection',
        },
    },
    
    # 큐 정의
    task_queues=[
        Queue('keyword_assessment', routing_key='keyword_assessment'),
        Queue('batch_processing', routing_key='batch_processing'),
        Queue('trend_analysis', routing_key='trend_analysis'),
        Queue('anomaly_detection', routing_key='anomaly_detection'),
    ],
    
    # 기본 큐
    task_default_queue='keyword_assessment',
    task_default_exchange='keyword_quality_assessment',
    task_default_routing_key='keyword_assessment',
    
    # 결과 설정
    result_expires=3600,  # 결과 1시간 후 삭제
    task_result_expires=3600,
    
    # 재시도 설정
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    
    # 모니터링 설정
    task_send_sent_event=True,
    task_track_started=True,
    worker_send_task_events=True,
    
    # 배치 처리 최적화
    task_always_eager=False,  # 개발 중에는 True로 설정 가능
    task_eager_propagates=True,
    task_ignore_result=False,
    
    # 성능 최적화
    broker_transport_options={
        'visibility_timeout': 3600,
        'fanout_prefix': True,
        'fanout_patterns': True,
    },
    
    # 작업 제한
    task_time_limit=1800,  # 30분
    task_soft_time_limit=1500,  # 25분
    
    # 에러 처리
    task_reject_on_worker_lost=True,
    task_acks_late=True,
)

# 작업 자동 발견
app.autodiscover_tasks([
    'app.tasks.keyword_assessment',
    'app.tasks.batch_processing',
    'app.tasks.trend_analysis',
    'app.tasks.anomaly_detection',
])

@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """워커 준비 완료 시 실행"""
    logger.info(f"Celery worker {sender} is ready")
    
    # Redis 연결 확인
    try:
        redis_client = redis.Redis.from_url(app.conf.broker_url)
        redis_client.ping()
        logger.info("Redis connection successful")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")

@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """워커 종료 시 실행"""
    logger.info(f"Celery worker {sender} is shutting down")

# 헬스 체크 작업
@app.task(bind=True, name='health_check')
def health_check(self):
    """워커 상태 확인"""
    return {
        'status': 'healthy',
        'worker_id': self.request.id,
        'timestamp': self.request.id,
    }

# 배치 작업 상태 관리
class BatchJobStatus:
    """배치 작업 상태 관리 클래스"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.prefix = "batch_job:"
    
    def create_job(self, batch_id: str, total_keywords: int):
        """배치 작업 생성"""
        job_key = f"{self.prefix}{batch_id}"
        job_data = {
            'batch_id': batch_id,
            'status': 'created',
            'total_keywords': total_keywords,
            'processed_keywords': 0,
            'failed_keywords': 0,
            'created_at': self.redis.time()[0],
        }
        self.redis.hset(job_key, mapping=job_data)
        self.redis.expire(job_key, 86400)  # 24시간 후 만료
        return job_data
    
    def update_job(self, batch_id: str, **kwargs):
        """배치 작업 상태 업데이트"""
        job_key = f"{self.prefix}{batch_id}"
        self.redis.hset(job_key, mapping=kwargs)
    
    def get_job(self, batch_id: str):
        """배치 작업 상태 조회"""
        job_key = f"{self.prefix}{batch_id}"
        return self.redis.hgetall(job_key)
    
    def increment_processed(self, batch_id: str):
        """처리된 키워드 수 증가"""
        job_key = f"{self.prefix}{batch_id}"
        self.redis.hincrby(job_key, 'processed_keywords', 1)
    
    def increment_failed(self, batch_id: str):
        """실패한 키워드 수 증가"""
        job_key = f"{self.prefix}{batch_id}"
        self.redis.hincrby(job_key, 'failed_keywords', 1)

# Redis 클라이언트 초기화
redis_client = redis.Redis.from_url(app.conf.broker_url)
batch_job_status = BatchJobStatus(redis_client)

# 애플리케이션 컨텍스트에 추가
app.batch_job_status = batch_job_status

if __name__ == '__main__':
    # 개발 모드에서 워커 실행
    # celery -A app.core.celery_app worker --loglevel=info --concurrency=4
    app.start()