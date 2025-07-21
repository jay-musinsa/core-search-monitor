#!/usr/bin/env python3
"""
Celery 태스크 실행 테스트
"""

import sys
import os
# tests 폴더에서 backend 폴더로 경로 추가
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from app.tasks.simple_keyword_assessment import simple_assess_single_keyword

def test_celery_single():
    """단일 Celery 태스크 테스트"""
    print("🚀 단일 Celery 태스크 테스트")
    print("=" * 40)
    
    keyword = "후드티"
    print(f"키워드: {keyword}")
    
    # Celery 태스크 실행
    task = simple_assess_single_keyword.delay(keyword, 'musinsa')
    print(f"📝 태스크 ID: {task.id}")
    print("⏳ 결과 대기 중...")
    
    try:
        result = task.get(timeout=30)
        print("🎉 성공!")
        print(f"📊 처리 시간: {result['processing_time']:.2f}초")
        print(f"📊 API 결과: {result['api_results']}개")
        return True
    except Exception as e:
        print(f"❌ 실패: {e}")
        return False

def test_celery_batch():
    """배치 Celery 태스크 테스트"""
    print("\n🔥 배치 Celery 태스크 테스트")
    print("=" * 40)
    
    keywords = ["코트", "자켓", "니트"]
    tasks = []
    
    # 여러 태스크 동시 실행
    for keyword in keywords:
        task = simple_assess_single_keyword.delay(keyword, 'musinsa')
        tasks.append((keyword, task))
        print(f"📝 '{keyword}' 태스크 시작: {task.id}")
    
    print("⏳ 모든 태스크 완료 대기...")
    
    # 결과 수집
    results = []
    for keyword, task in tasks:
        try:
            result = task.get(timeout=60)
            results.append((keyword, True, result))
            print(f"✅ '{keyword}' 완료")
        except Exception as e:
            results.append((keyword, False, str(e)))
            print(f"❌ '{keyword}' 실패: {e}")
    
    # 요약
    successful = sum(1 for _, success, _ in results if success)
    print(f"\n📊 배치 결과: {successful}/{len(keywords)} 성공")
    
    return successful == len(keywords)

if __name__ == '__main__':
    print("🔍 Celery 태스크 종합 테스트")
    print("=" * 60)
    
    # 단일 태스크 테스트
    single_ok = test_celery_single()
    
    # 배치 태스크 테스트
    batch_ok = test_celery_batch()
    
    print("\n" + "=" * 60)
    if single_ok and batch_ok:
        print("🎉 모든 Celery 태스크 테스트 성공!")
        print("✅ assess_single_keyword가 Celery에서 완벽하게 작동합니다!")
    else:
        print("⚠️ 일부 테스트 실패")
    
    print("\n💡 사용 방법:")
    print("python run_assess.py celery <키워드>")
    print("python -c \"from simple_assess_keyword import simple_assess_single_keyword; print(simple_assess_single_keyword.delay('키워드').get())\"") 