#!/usr/bin/env python3
"""
Celery 배치 처리 시스템 테스트 스크립트
"""

import asyncio
import time
from typing import List
import sys
import os

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, '/Users/jayko/devhub-musinsa/core-search-monitor/backend')

from app.tasks.keyword_assessment import assess_keyword_async
from app.tasks.batch_processing import start_batch_processing, check_batch_status
from app.core.celery_app import app, health_check

def test_single_keyword():
    """단일 키워드 평가 테스트"""
    print("=== 단일 키워드 평가 테스트 ===")
    
    # 테스트 키워드
    test_keyword = "원피스"
    
    print(f"키워드 '{test_keyword}' 평가 시작...")
    
    # 작업 시작
    task_id = assess_keyword_async(test_keyword, platform='musinsa')
    print(f"작업 ID: {task_id}")
    
    # 작업 상태 모니터링
    from celery.result import AsyncResult
    result = AsyncResult(task_id, app=app)
    
    print("작업 상태 모니터링 중...")
    while not result.ready():
        print(f"상태: {result.state}")
        time.sleep(5)
    
    if result.successful():
        print("✅ 작업 완료!")
        print(f"결과: {result.result}")
    else:
        print("❌ 작업 실패!")
        print(f"에러: {result.traceback}")

def test_batch_processing():
    """배치 처리 테스트"""
    print("\n=== 배치 처리 테스트 ===")
    
    # 테스트 키워드 목록
    test_keywords = [
        "원피스",
        "청바지", 
        "운동화",
        "백팩",
        "시계"
    ]
    
    print(f"키워드 {len(test_keywords)}개 배치 처리 시작...")
    print(f"키워드: {test_keywords}")
    
    # 배치 처리 시작
    batch_task_id = start_batch_processing(test_keywords, platform='musinsa')
    print(f"배치 작업 ID: {batch_task_id}")
    
    # 배치 상태 모니터링
    from celery.result import AsyncResult
    batch_result = AsyncResult(batch_task_id, app=app)
    
    print("배치 작업 상태 모니터링 중...")
    while not batch_result.ready():
        print(f"상태: {batch_result.state}")
        time.sleep(10)
    
    if batch_result.successful():
        print("✅ 배치 처리 완료!")
        result = batch_result.result
        print(f"성공: {result['successful_count']}, 실패: {result['failed_count']}")
        print(f"총 처리 시간: {result['total_processing_time']:.2f}초")
        print(f"평균 처리 시간: {result['avg_processing_time']:.2f}초")
    else:
        print("❌ 배치 처리 실패!")
        print(f"에러: {batch_result.traceback}")

def test_health_check():
    """헬스 체크 테스트"""
    print("\n=== 헬스 체크 테스트 ===")
    
    # 헬스 체크 작업 실행
    health_task = health_check.apply_async()
    
    try:
        result = health_task.get(timeout=10)
        print("✅ 헬스 체크 성공!")
        print(f"결과: {result}")
    except Exception as e:
        print("❌ 헬스 체크 실패!")
        print(f"에러: {e}")

def test_worker_info():
    """워커 정보 테스트"""
    print("\n=== 워커 정보 테스트 ===")
    
    # 활성 워커 조회
    try:
        inspect = app.control.inspect()
        
        # 활성 작업
        active_tasks = inspect.active()
        print(f"활성 작업: {active_tasks}")
        
        # 워커 통계
        stats = inspect.stats()
        print(f"워커 통계: {stats}")
        
        # 등록된 작업
        registered_tasks = inspect.registered()
        print(f"등록된 작업: {registered_tasks}")
        
    except Exception as e:
        print(f"워커 정보 조회 실패: {e}")

def main():
    """메인 테스트 실행"""
    print("Celery 배치 처리 시스템 테스트 시작")
    print("=" * 50)
    
    # 사용자 선택
    print("테스트 선택:")
    print("1. 헬스 체크")
    print("2. 워커 정보")
    print("3. 단일 키워드 평가")
    print("4. 배치 처리")
    print("5. 전체 테스트")
    
    choice = input("선택 (1-5): ")
    
    if choice == "1":
        test_health_check()
    elif choice == "2":
        test_worker_info()
    elif choice == "3":
        test_single_keyword()
    elif choice == "4":
        test_batch_processing()
    elif choice == "5":
        test_health_check()
        test_worker_info()
        test_single_keyword()
        test_batch_processing()
    else:
        print("잘못된 선택입니다.")
        return
    
    print("\n테스트 완료!")

if __name__ == "__main__":
    main()