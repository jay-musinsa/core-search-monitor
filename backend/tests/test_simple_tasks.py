#!/usr/bin/env python3
"""
간단한 Celery 태스크 실행 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("🚀 Celery 태스크 실행 방법 가이드")
print("=" * 50)

# 1. 헬스 체크 태스크 (가장 간단)
print("1️⃣ 헬스 체크 태스크:")
print("from app.core.celery_app import health_check")
print("task = health_check.delay()")
print("result = task.get(timeout=10)")
print()

# 2. 배치 처리 태스크
print("2️⃣ 배치 처리 태스크:")
print("from app.tasks.batch_processing import process_batch_keywords")
print("keywords = ['스니커즈', '맨투맨', '청바지']")
print("task = process_batch_keywords.delay(keywords, 'musinsa')")
print("print(f'배치 ID: {task.id}')")
print("print(f'상태: {task.status}')")
print()

# 3. 단일 키워드 평가
print("3️⃣ 단일 키워드 평가:")
print("from app.tasks.keyword_assessment import assess_single_keyword")
print("task = assess_single_keyword.delay('스니커즈', 'musinsa')")
print("result = task.get(timeout=60)  # 결과 대기")
print()

# 4. 일일 키워드 평가
print("4️⃣ 일일 키워드 평가:")
print("from app.tasks.batch_processing import daily_keyword_assessment")
print("task = daily_keyword_assessment.delay()")
print("print(f'일일 평가 시작: {task.id}')")
print()

# 5. 배치 상태 확인
print("5️⃣ 배치 상태 확인:")
print("from app.tasks.batch_processing import get_batch_status")
print("task = get_batch_status.delay('배치_ID')")
print("status = task.get()")
print()

# 6. 비동기 실행 (결과 대기 안함)
print("6️⃣ 비동기 실행 (백그라운드):")
print("task = process_batch_keywords.delay(keywords)")
print("print(f'태스크 시작됨: {task.id}')")
print("# Flower에서 진행상황 확인: http://localhost:5555")
print()

print("💡 팁:")
print("- .delay()는 비동기 실행")
print("- .get()은 결과 대기 (동기)")
print("- timeout 설정으로 대기시간 제한")
print("- Flower에서 실시간 모니터링 가능")

# 실제 실행 예제
if __name__ == '__main__':
    print("\n🔧 실제 실행 테스트:")
    
    try:
        from app.core.celery_app import health_check
        print("✅ 헬스 체크 태스크 로드 성공")
        
        # 비동기 실행만 테스트 (결과 대기 안함)
        task = health_check.delay()
        print(f"✅ 헬스 체크 실행됨 - ID: {task.id}")
        print(f"📊 상태: {task.status}")
        
    except Exception as e:
        print(f"❌ 에러: {e}")
    
    print("\n🌸 Flower 웹에서 확인하세요: http://localhost:5555") 