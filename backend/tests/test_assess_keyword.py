#!/usr/bin/env python3
"""
assess_single_keyword 태스크 테스트
"""

import sys
import os
import time

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_assess_single_keyword():
    """assess_single_keyword 태스크 실행 테스트"""
    print("🔍 assess_single_keyword 태스크 테스트 시작")
    print("=" * 50)
    
    try:
        # 태스크 임포트
        from app.tasks.keyword_assessment import assess_single_keyword
        print("✅ assess_single_keyword 태스크 임포트 성공")
        
        # 테스트 키워드와 플랫폼
        keyword = "스니커즈"
        platform = "musinsa"
        
        print(f"🔍 테스트 키워드: '{keyword}' (플랫폼: {platform})")
        
        # 태스크 실행
        print("🚀 assess_single_keyword 태스크 실행 중...")
        task = assess_single_keyword.delay(keyword, platform)
        
        print(f"📝 태스크 ID: {task.id}")
        print(f"📊 초기 상태: {task.status}")
        
        # 상태 모니터링 (최대 60초 대기)
        timeout = 60
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            current_status = task.status
            elapsed = int(time.time() - start_time)
            
            print(f"⏳ 대기 중... ({elapsed}/{timeout}초) - 상태: {current_status}")
            
            if current_status in ['SUCCESS', 'FAILURE', 'REVOKED']:
                break
                
            time.sleep(5)  # 5초마다 체크
        
        # 결과 확인
        try:
            print("\n🔍 결과 확인 중...")
            result = task.get(timeout=10)
            
            print("🎉 assess_single_keyword 실행 성공!")
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
            
            return True, task.id, result
            
        except Exception as e:
            print(f"❌ 결과 확인 실패: {e}")
            
            # 태스크 상태 재확인
            print(f"📊 최종 상태: {task.status}")
            
            if task.status == 'FAILURE':
                try:
                    error_info = task.result  # 실패 정보
                    print(f"❌ 실패 원인: {error_info}")
                except:
                    print("❌ 실패 원인을 가져올 수 없습니다")
            
            return False, task.id, None
            
    except Exception as e:
        print(f"❌ assess_single_keyword 테스트 실패: {e}")
        import traceback
        print("스택 트레이스:")
        print(traceback.format_exc())
        return False, None, None

def check_dependencies():
    """의존성 확인"""
    print("🔧 의존성 확인 중...")
    
    dependencies = []
    
    try:
        import clickhouse_connect
        print("✅ ClickHouse 클라이언트 사용 가능")
        
        # ClickHouse 연결 테스트
        client = clickhouse_connect.get_client(
            host='localhost', port=8123, username='default', password=''
        )
        client.ping()
        print("✅ ClickHouse 서버 연결 성공")
        dependencies.append(True)
        
    except Exception as e:
        print(f"❌ ClickHouse 연결 실패: {e}")
        dependencies.append(False)
    
    try:
        import redis
        r = redis.Redis.from_url('redis://localhost:6379/1')
        r.ping()
        print("✅ Redis 서버 연결 성공")
        dependencies.append(True)
    except Exception as e:
        print(f"❌ Redis 연결 실패: {e}")
        dependencies.append(False)
    
    try:
        from app.core.crawler import CrawlerMusinsa
        print("✅ 크롤러 모듈 사용 가능")
        dependencies.append(True)
    except Exception as e:
        print(f"❌ 크롤러 모듈 실패: {e}")
        dependencies.append(False)
    
    try:
        from app.core.gpt import GPTMetricEvaluator
        print("✅ GPT 평가기 모듈 사용 가능")
        dependencies.append(True)
    except Exception as e:
        print(f"❌ GPT 평가기 모듈 실패: {e}")
        dependencies.append(False)
    
    return all(dependencies)

if __name__ == '__main__':
    print("🔍 assess_single_keyword 종합 테스트")
    print("=" * 60)
    
    # 1. 의존성 확인
    deps_ok = check_dependencies()
    print()
    
    if not deps_ok:
        print("⚠️ 일부 의존성에 문제가 있습니다. 테스트를 계속 진행합니다.")
        print()
    
    # 2. 태스크 실행 테스트
    success, task_id, result = test_assess_single_keyword()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 assess_single_keyword 테스트 성공!")
        print(f"📝 태스크 ID: {task_id}")
        print("🌸 Flower에서 더 자세히 확인: http://localhost:5555")
    else:
        print("❌ assess_single_keyword 테스트 실패")
        if task_id:
            print(f"📝 실패한 태스크 ID: {task_id}")
        print("💡 로그를 확인하고 의존성을 점검해주세요") 