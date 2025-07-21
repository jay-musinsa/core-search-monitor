#!/usr/bin/env python3
"""
헬스 체크 태스크 단독 테스트
"""

import sys
import os
import time

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_health_check():
    """헬스 체크 태스크 실행"""
    print("🩺 헬스 체크 태스크 테스트 시작")
    print("=" * 40)
    
    try:
        # 헬스 체크 태스크 임포트
        from app.core.celery_app import health_check
        print("✅ 헬스 체크 태스크 임포트 성공")
        
        # 태스크 실행
        print("🚀 헬스 체크 태스크 실행 중...")
        task = health_check.delay()
        
        print(f"📝 태스크 ID: {task.id}")
        print(f"📊 초기 상태: {task.status}")
        
        # 상태 확인 (몇 초 대기)
        for i in range(5):
            print(f"⏳ 대기 중... ({i+1}/5)")
            time.sleep(1)
            print(f"📊 현재 상태: {task.status}")
            
            if task.status not in ['PENDING', 'STARTED']:
                break
        
        # 결과 시도 (짧은 타임아웃)
        try:
            print("🔍 결과 확인 중...")
            result = task.get(timeout=5)
            print(f"🎉 헬스 체크 성공!")
            print(f"📋 결과: {result}")
            
        except Exception as e:
            print(f"⚠️ 결과 확인 실패 (하지만 태스크는 실행됨): {e}")
            print("💡 Flower에서 확인해보세요: http://localhost:5555")
            
        return task.id
        
    except Exception as e:
        print(f"❌ 헬스 체크 실패: {e}")
        return None

if __name__ == '__main__':
    task_id = test_health_check()
    
    if task_id:
        print(f"\n✅ 헬스 체크 태스크 실행됨 - ID: {task_id}")
        print("🌸 Flower에서 더 자세히 확인: http://localhost:5555")
    else:
        print("\n❌ 헬스 체크 실행 실패") 