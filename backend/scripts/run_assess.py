#!/usr/bin/env python3
"""
assess_single_keyword 간편 실행 스크립트
"""

import sys
import os
# scripts 폴더에서 backend 폴더로 경로 추가
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

def run_single_keyword(keyword, platform="musinsa"):
    """단일 키워드 평가 실행"""
    print(f"🔍 키워드 '{keyword}' 평가 시작 (플랫폼: {platform})")
    
    try:
        from app.tasks.simple_keyword_assessment import simple_assess_single_keyword
        
        # 직접 실행
        result = simple_assess_single_keyword(keyword, platform)
        
        print("🎉 평가 완료!")
        print(f"📊 결과:")
        print(f"   - Assessment ID: {result['assessment_id']}")
        print(f"   - 처리 시간: {result['processing_time']:.2f}초")
        print(f"   - API 결과 수: {result['api_results']}")
        print(f"   - GPT 점수:")
        print(f"     * NDCG: {result['gpt_scores']['ndcg_score']}")
        print(f"     * Precision: {result['gpt_scores']['precision']}")
        print(f"     * Recall: {result['gpt_scores']['recall']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 평가 실패: {e}")
        return False

def run_celery_task(keyword, platform="musinsa"):
    """Celery 태스크로 실행"""
    print(f"🚀 Celery 태스크로 '{keyword}' 평가 시작")
    
    try:
        from app.tasks.simple_keyword_assessment import simple_assess_single_keyword
        
        # Celery 태스크 실행
        task = simple_assess_single_keyword.delay(keyword, platform)
        print(f"✅ 태스크 실행됨: {task.id}")
        print("⏳ 결과 대기 중...")
        
        # 결과 대기
        result = task.get(timeout=60)
        
        print("🎉 Celery 태스크 완료!")
        print(f"📊 결과:")
        print(f"   - Assessment ID: {result['assessment_id']}")
        print(f"   - 처리 시간: {result['processing_time']:.2f}초")
        
        return True
        
    except Exception as e:
        print(f"❌ Celery 태스크 실패: {e}")
        print("💡 워커가 실행 중인지 확인하세요")
        return False

def run_batch_keywords(keywords, platform="musinsa"):
    """여러 키워드 배치 처리"""
    print(f"📦 배치 처리 시작: {len(keywords)}개 키워드")
    
    results = []
    
    for i, keyword in enumerate(keywords, 1):
        print(f"\n[{i}/{len(keywords)}] '{keyword}' 처리 중...")
        
        success = run_single_keyword(keyword, platform)
        results.append((keyword, success))
    
    # 결과 요약
    print(f"\n📊 배치 처리 완료:")
    successful = sum(1 for _, success in results if success)
    print(f"   - 성공: {successful}/{len(keywords)}")
    print(f"   - 실패: {len(keywords) - successful}/{len(keywords)}")
    
    return results

if __name__ == '__main__':
    print("🔍 assess_single_keyword 실행 스크립트")
    print("=" * 50)
    
    # 사용법 안내
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python run_assess.py <키워드>")
        print("  python run_assess.py <키워드> <플랫폼>")
        print("  python run_assess.py batch '키워드1,키워드2,키워드3'")
        print("  python run_assess.py celery <키워드>")
        print()
        print("예시:")
        print("  python run_assess.py 스니커즈")
        print("  python run_assess.py 맨투맨 musinsa")
        print("  python run_assess.py batch '스니커즈,맨투맨,청바지'")
        print("  python run_assess.py celery 후드티")
        sys.exit(1)
    
    mode = sys.argv[1]
    
    if mode == "batch":
        # 배치 모드
        if len(sys.argv) < 3:
            print("❌ 배치 모드에는 키워드 목록이 필요합니다")
            print("예시: python run_assess.py batch '스니커즈,맨투맨,청바지'")
            sys.exit(1)
        
        keywords = [k.strip() for k in sys.argv[2].split(',')]
        platform = sys.argv[3] if len(sys.argv) > 3 else "musinsa"
        
        run_batch_keywords(keywords, platform)
        
    elif mode == "celery":
        # Celery 모드
        if len(sys.argv) < 3:
            print("❌ Celery 모드에는 키워드가 필요합니다")
            sys.exit(1)
        
        keyword = sys.argv[2]
        platform = sys.argv[3] if len(sys.argv) > 3 else "musinsa"
        
        run_celery_task(keyword, platform)
        
    else:
        # 단일 키워드 모드 (기본)
        keyword = sys.argv[1]
        platform = sys.argv[2] if len(sys.argv) > 2 else "musinsa"
        
        run_single_keyword(keyword, platform) 