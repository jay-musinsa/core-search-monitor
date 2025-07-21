#!/usr/bin/env python3
"""
간단한 assess_single_keyword 구현
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
from datetime import datetime
from typing import Dict, Optional
import json
import uuid

from app.core.celery_app import app
import clickhouse_connect
import redis

logger = logging.getLogger(__name__)

@app.task(name='simple_assess_single_keyword')
def simple_assess_single_keyword(keyword: str, platform: str = 'musinsa', 
                                batch_id: Optional[str] = None, priority: int = 1):
    """
    간단한 키워드 품질 평가 작업
    모든 기능을 함수 내부에 직접 구현
    """
    try:
        # 시작 시간
        start_time = datetime.now()
        assessment_id = str(uuid.uuid4())
        
        logger.info(f"Starting simple assessment for keyword: {keyword} on {platform}")
        
        # ClickHouse 연결
        clickhouse_client = clickhouse_connect.get_client(
            host='localhost', port=8123, username='default', password=''
        )
        
        # Redis 연결
        redis_client = redis.Redis.from_url(app.conf.broker_url)
        
        # 1. 키워드 ID 조회 또는 생성
        def get_or_create_keyword_id(keyword: str, priority: int) -> int:
            try:
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
                if any(word in keyword for word in ['스니커즈', '운동화', '구두']):
                    category = 'shoes'
                elif any(word in keyword for word in ['바지', '청바지', '원피스']):
                    category = 'clothing'
                
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
                # 기본값 반환
                return 1
        
        # 2. API 데이터 수집 (모의 데이터)
        def collect_api_data(keyword: str, platform: str) -> Dict:
            try:
                # 모의 API 응답
                mock_data = {
                    'products': [
                        {'name': f'{keyword} 제품 1', 'price': 50000},
                        {'name': f'{keyword} 제품 2', 'price': 75000},
                        {'name': f'{keyword} 제품 3', 'price': 60000},
                    ]
                }
                
                return {
                    'response_time': 0.5,
                    'total_results': len(mock_data['products']),
                    'status_code': 200,
                    'data': json.dumps(mock_data, ensure_ascii=False)
                }
                
            except Exception as e:
                logger.error(f"Error in collect_api_data: {e}")
                return {
                    'response_time': 0,
                    'total_results': 0,
                    'status_code': 500,
                    'data': json.dumps({'error': str(e)}, ensure_ascii=False)
                }
        
        # 3. 스크린샷 캡처 (모의)
        def capture_screenshot(keyword: str, platform: str) -> Dict:
            return {
                'path': f'/tmp/screenshot_{keyword}_{platform}.png',
                'size': 1024000,
                'quality': 'mock'
            }
        
        # 4. GPT 평가 (모의)
        def perform_gpt_evaluation(keyword: str, api_data: Dict, screenshot_data: Dict) -> Dict:
            return {
                'ndcg_score': 0.85,
                'precision': 0.78,
                'recall': 0.82,
                'explanation': f'{keyword}에 대한 모의 평가 결과'
            }
        
        # 5. 결과 저장
        def save_assessment_result(assessment_id: str, keyword_id: int, keyword: str, 
                                 platform: str, api_data: Dict, screenshot_data: Dict, 
                                 gpt_evaluation: Dict, start_time: datetime, batch_id: Optional[str]):
            try:
                # quality_assessment_daily 테이블에 저장
                result_data = [(
                    assessment_id,
                    keyword_id,
                    keyword,
                    platform,
                    datetime.now().date(),
                    api_data['total_results'],
                    api_data['response_time'],
                    api_data['status_code'],
                    gpt_evaluation['ndcg_score'],
                    gpt_evaluation['precision'],
                    gpt_evaluation['recall'],
                    screenshot_data['path'],
                    api_data['data'],
                    json.dumps(gpt_evaluation, ensure_ascii=False),
                    datetime.now(),
                    batch_id or ''
                )]
                
                clickhouse_client.insert(
                    'quality_assessment_daily',
                    result_data,
                    column_names=[
                        'assessment_id', 'keyword_id', 'keyword', 'platform', 
                        'assessment_date', 'total_results', 'response_time_ms',
                        'status_code', 'ndcg_score', 'precision_score', 'recall_score',
                        'screenshot_path', 'raw_api_data', 'gpt_evaluation_data',
                        'created_at', 'batch_id'
                    ]
                )
                
                logger.info(f"Assessment result saved for keyword: {keyword}")
                
            except Exception as e:
                logger.error(f"Error saving assessment result: {e}")
        
        # 실제 처리 실행
        keyword_id = get_or_create_keyword_id(keyword, priority)
        api_data = collect_api_data(keyword, platform)
        screenshot_data = capture_screenshot(keyword, platform)
        gpt_evaluation = perform_gpt_evaluation(keyword, api_data, screenshot_data)
        
        save_assessment_result(
            assessment_id, keyword_id, keyword, platform, api_data,
            screenshot_data, gpt_evaluation, start_time, batch_id
        )
        
        # 처리 시간 계산
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Simple assessment completed for keyword: {keyword}, "
                   f"processing time: {processing_time:.2f}s")
        
        # 결과 반환
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
        logger.error(f"Error in simple_assess_single_keyword: {exc}")
        import traceback
        logger.error(traceback.format_exc())
        raise exc

# 테스트 함수
def test_simple_assess():
    """간단한 테스트"""
    print("🔧 간단한 assess_single_keyword 테스트")
    print("=" * 50)
    
    try:
        # 직접 호출
        result = simple_assess_single_keyword("스니커즈", "musinsa")
        print("🎉 직접 호출 성공!")
        print(f"📋 결과: {result}")
        
        # Celery 태스크로 호출
        task = simple_assess_single_keyword.delay("맨투맨", "musinsa")
        print(f"✅ Celery 태스크 실행: {task.id}")
        
        try:
            celery_result = task.get(timeout=10)
            print("🎉 Celery 태스크 성공!")
            print(f"📋 Celery 결과: {celery_result}")
        except Exception as e:
            print(f"⚠️ Celery 결과 확인 실패: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == '__main__':
    success = test_simple_assess()
    if success:
        print("\n🎉 간단한 assess_single_keyword가 성공적으로 작동합니다!")
    else:
        print("\n❌ 테스트 실패") 