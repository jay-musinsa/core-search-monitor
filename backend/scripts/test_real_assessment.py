#!/usr/bin/env python3
"""
실제 core 서비스들을 사용한 키워드 평가 테스트 스크립트
무신사 API + 스크린샷 캡처 + GPT 평가를 통합 수행
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tasks.keyword_assessment import assess_single_keyword


def test_keyword_assessment(keyword: str, platform: str = 'musinsa'):
    """키워드 품질 평가 테스트"""
    print(f"🚀 키워드 '{keyword}' 평가 시작 (플랫폼: {platform})")
    print("📋 실행되는 과정:")
    print("   1. 무신사 API 호출하여 상품 데이터 수집")
    print("   2. 무신사/29CM 검색 페이지 스크린샷 캡처")
    print("   3. GPT Vision API로 검색 품질 평가")
    print("   4. 결과를 ClickHouse에 저장")
    print("-" * 50)
    
    try:
        # Celery task 실행
        task = assess_single_keyword.delay(keyword, platform)
        print(f"📝 Celery Task ID: {task.id}")
        print("⏳ 처리 중... (보통 20-30초 소요)")
        
        # 결과 대기
        result = task.get(timeout=60)
        
        # 결과 출력
        print("\n🎉 평가 완료!")
        print(f"📊 결과 요약:")
        print(f"   - 키워드: {result['keyword']}")
        print(f"   - 플랫폼: {result['platform']}")
        print(f"   - 처리시간: {result['processing_time']:.2f}초")
        print(f"   - 상태: {result['status']}")
        
        print(f"\n🤖 GPT 평가 점수:")
        gpt_scores = result['gpt_scores']
        print(f"   - NDCG@10: {gpt_scores['ndcg_score']}")
        print(f"   - Precision: {gpt_scores['precision']}")
        print(f"   - Recall: {gpt_scores['recall']}")
        
        print(f"\n📈 데이터 수집 결과:")
        print(f"   - API 상품 수: {result['api_results']}개")
        print(f"   - 스크린샷: {'✓' if result['screenshot_path'] else '✗'}")
        if result['screenshot_path']:
            print(f"     경로: {result['screenshot_path']}")
        
        # 상세 정보
        details = result.get('evaluation_details', {})
        if details:
            print(f"\n🔍 플랫폼별 상세 평가:")
            
            musinsa = details.get('musinsa', {})
            if musinsa:
                print(f"   무신사:")
                print(f"     - NDCG: {musinsa.get('ndcg@10', 'N/A')}")
                print(f"     - Precision: {musinsa.get('precision', 'N/A')}")
                print(f"     - 스크린샷: {'✓' if musinsa.get('screenshot') else '✗'}")
                
                issues = musinsa.get('precision_issues', [])
                if issues:
                    print(f"     - Precision 이슈 상품: {len(issues)}개")
                    for i, issue in enumerate(issues[:5]):  # 처음 5개만
                        name = issue.get('goods_name', 'Unknown')[:30]
                        print(f"       #{i+1}: {name}...")
            
            cm29 = details.get('29cm', {})
            if cm29:
                print(f"   29CM:")
                print(f"     - NDCG: {cm29.get('ndcg@10', 'N/A')}")
                print(f"     - Precision: {cm29.get('precision', 'N/A')}")
                print(f"     - 스크린샷: {'✓' if cm29.get('screenshot') else '✗'}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ 평가 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """메인 실행 함수"""
    if len(sys.argv) < 2:
        print("사용법: python test_real_assessment.py <키워드> [플랫폼]")
        print("예시:")
        print("  python test_real_assessment.py 스니커즈")
        print("  python test_real_assessment.py 청바지 musinsa")
        print("  python test_real_assessment.py 원피스 29cm")
        return
    
    keyword = sys.argv[1]
    platform = sys.argv[2] if len(sys.argv) > 2 else 'musinsa'
    
    # Celery worker 상태 확인
    try:
        from celery import Celery
        app = Celery('keyword_quality_assessment')
        app.conf.update(
            broker_url='redis://localhost:6379/1',
            result_backend='redis://localhost:6379/2'
        )
        
        inspect = app.control.inspect()
        workers = inspect.active()
        
        if not workers:
            print("⚠️ Celery worker가 실행되지 않은 것 같습니다.")
            print("다음 명령으로 워커를 시작하세요:")
            print("  celery -A app.core.celery_app worker --loglevel=info --concurrency=2 --detach")
            return
            
        print(f"✅ Celery worker 실행 중 ({len(workers)}개)")
        
    except Exception as e:
        print(f"⚠️ Celery 상태 확인 실패: {e}")
    
    # 평가 실행
    result = test_keyword_assessment(keyword, platform)
    
    if result:
        print(f"\n✅ '{keyword}' 키워드 평가가 성공적으로 완료되었습니다!")
        print("📝 Assessment ID:", result['assessment_id'])
    else:
        print(f"\n❌ '{keyword}' 키워드 평가에 실패했습니다.")


if __name__ == "__main__":
    main() 