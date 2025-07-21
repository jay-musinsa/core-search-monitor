#!/usr/bin/env python3
"""
Celery 태스크 실행 테스트 스크립트
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.celery_app import app
from app.tasks.batch_processing import (
    process_batch_keywords, 
    daily_keyword_assessment, 
    get_batch_status,
    cleanup_old_batches
)

def test_health_check():
    """헬스 체크 태스크 실행"""
    print("🔍 헬스 체크 실행 중...")
    
    # 동기 실행
    from app.core.celery_app import health_check
    task = health_check.delay()
    result = task.get(timeout=10)
    
    print(f"✅ 헬스 체크 결과: {result}")
    return task.id, result

def test_single_keyword():
    """단일 키워드 평가 실행"""
    print("🔍 단일 키워드 평가 실행 중...")
    
    from app.tasks.keyword_assessment import assess_single_keyword
    
    keyword = "스니커즈"
    platform = "musinsa"
    
    task = assess_single_keyword.delay(keyword, platform)
    print(f"📝 태스크 ID: {task.id}")
    print(f"📊 상태: {task.status}")
    
    try:
        # 30초 대기
        result = task.get(timeout=30)
        print(f"✅ 결과: {result}")
        return task.id, result
    except Exception as e:
        print(f"❌ 에러: {e}")
        return task.id, None

def test_batch_processing():
    """배치 처리 실행"""
    print("🔍 배치 처리 실행 중...")
    
    keywords = ['스니커즈', '맨투맨', '청바지']
    platform = 'musinsa'
    
    task = process_batch_keywords.delay(keywords, platform, batch_size=2)
    print(f"📝 배치 ID: {task.id}")
    print(f"📊 상태: {task.status}")
    
    try:
        # 5분 대기
        result = task.get(timeout=300)
        print(f"✅ 배치 처리 완료!")
        print(f"📊 처리 결과: {result['successful_count']}/{result['total_keywords']} 성공")
        return task.id, result
    except Exception as e:
        print(f"❌ 에러: {e}")
        return task.id, None

def test_batch_status(batch_id):
    """배치 상태 확인"""
    print(f"🔍 배치 상태 확인 중: {batch_id}")
    
    task = get_batch_status.delay(batch_id)
    result = task.get(timeout=10)
    
    print(f"📊 배치 상태: {result}")
    return result

def test_daily_assessment():
    """일일 키워드 평가 실행"""
    print("🔍 일일 키워드 평가 실행 중...")
    
    task = daily_keyword_assessment.delay()
    print(f"📝 태스크 ID: {task.id}")
    print(f"📊 상태: {task.status}")
    
    # 비동기 실행 (결과 대기 안함)
    print("⏳ 백그라운드에서 실행 중... (Flower에서 확인 가능)")
    return task.id

def test_cleanup():
    """오래된 배치 정리"""
    print("🔍 오래된 배치 정리 실행 중...")
    
    task = cleanup_old_batches.delay(days_old=1)
    result = task.get(timeout=30)
    
    print(f"🧹 정리 완료: {result}")
    return result

if __name__ == '__main__':
    print("🚀 Celery 태스크 테스트 시작!")
    print("=" * 50)
    
    # 1. 헬스 체크
    try:
        test_health_check()
        print()
    except Exception as e:
        print(f"❌ 헬스 체크 실패: {e}")
        print()
    
    # 2. 단일 키워드 테스트
    try:
        task_id, result = test_single_keyword()
        print()
    except Exception as e:
        print(f"❌ 단일 키워드 실패: {e}")
        print()
    
    # 3. 배치 처리 테스트
    try:
        batch_id, batch_result = test_batch_processing()
        print()
        
        # 배치 상태 확인
        if batch_id:
            test_batch_status(batch_id)
            print()
            
    except Exception as e:
        print(f"❌ 배치 처리 실패: {e}")
        print()
    
    # 4. 일일 평가 (백그라운드 실행)
    try:
        daily_task_id = test_daily_assessment()
        print()
    except Exception as e:
        print(f"❌ 일일 평가 실패: {e}")
        print()
    
    # 5. 정리 작업
    try:
        test_cleanup()
        print()
    except Exception as e:
        print(f"❌ 정리 작업 실패: {e}")
        print()
    
    print("✅ 테스트 완료!")
    print("🌸 Flower에서 더 자세한 정보 확인: http://localhost:5555") 