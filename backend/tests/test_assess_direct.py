#!/usr/bin/env python3
"""
assess_single_keyword 직접 테스트 (Celery 워커 없이)
"""

import sys
import os
import time

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_assess_direct():
    """assess_single_keyword 함수를 직접 호출해서 테스트"""
    print("🔧 assess_single_keyword 직접 호출 테스트")
    print("=" * 50)
    
    try:
        # 함수 임포트
        from app.tasks.keyword_assessment import assess_single_keyword
        print("✅ assess_single_keyword 함수 임포트 성공")
        
        # 테스트 키워드
        keyword = "스니커즈"
        platform = "musinsa"
        
        print(f"🔍 테스트 키워드: '{keyword}' (플랫폼: {platform})")
        print("🚀 함수 직접 실행 중...")
        
        start_time = time.time()
        
        # 함수 직접 호출 (Celery 태스크가 아닌 일반 함수로 호출)
        result = assess_single_keyword(keyword, platform)
        
        end_time = time.time()
        
        print(f"🎉 함수 실행 성공! (실행 시간: {end_time - start_time:.2f}초)")
        print("📋 결과:")
        print(f"   - Assessment ID: {result.get('assessment_id', 'N/A')}")
        print(f"   - 키워드: {result.get('keyword', 'N/A')}")
        print(f"   - 플랫폼: {result.get('platform', 'N/A')}")
        print(f"   - 상태: {result.get('status', 'N/A')}")
        print(f"   - 처리 시간: {result.get('processing_time', 0):.2f}초")
        print(f"   - API 결과 수: {result.get('api_results', 0)}")
        
        # GPT 점수 출력
        gpt_scores = result.get('gpt_scores', {})
        if gpt_scores:
            print("   - GPT 평가 점수:")
            print(f"     * NDCG: {gpt_scores.get('ndcg_score', 0)}")
            print(f"     * Precision: {gpt_scores.get('precision', 0)}")
            print(f"     * Recall: {gpt_scores.get('recall', 0)}")
        
        return True, result
        
    except Exception as e:
        print(f"❌ 직접 호출 테스트 실패: {e}")
        import traceback
        print("스택 트레이스:")
        print(traceback.format_exc())
        return False, None

def test_celery_task():
    """Celery 태스크로 실행 테스트"""
    print("\n🔍 Celery 태스크 실행 테스트")
    print("=" * 50)
    
    try:
        from app.tasks.keyword_assessment import assess_single_keyword
        
        # Celery 태스크로 실행
        task = assess_single_keyword.delay("스니커즈", "musinsa")
        print(f"✅ Celery 태스크 실행됨")
        print(f"📝 태스크 ID: {task.id}")
        print(f"📊 상태: {task.status}")
        
        # 짧은 대기 후 결과 확인 시도
        try:
            result = task.get(timeout=10)
            print("🎉 Celery 태스크 성공!")
            return True, task.id
        except Exception as e:
            print(f"⚠️ 결과 확인 실패: {e}")
            print("💡 워커가 실행되지 않았거나 다른 문제가 있을 수 있습니다")
            return False, task.id
            
    except Exception as e:
        print(f"❌ Celery 태스크 실행 실패: {e}")
        return False, None

if __name__ == '__main__':
    print("🔍 assess_single_keyword 종합 테스트")
    print("=" * 60)
    
    # 1. 직접 호출 테스트
    direct_success, direct_result = test_assess_direct()
    
    # 2. Celery 태스크 테스트  
    celery_success, celery_task_id = test_celery_task()
    
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약:")
    print(f"   - 직접 호출: {'✅ 성공' if direct_success else '❌ 실패'}")
    print(f"   - Celery 태스크: {'✅ 성공' if celery_success else '❌ 실패'}")
    
    if direct_success and celery_success:
        print("\n🎉 모든 테스트 통과! assess_single_keyword가 정상 작동합니다!")
    elif direct_success:
        print("\n⚠️ 함수는 정상이지만 Celery 설정에 문제가 있을 수 있습니다")
        print("💡 워커를 재시작하거나 설정을 확인해보세요")
    else:
        print("\n❌ 함수 자체에 문제가 있습니다. 코드를 재검토해야 합니다") 