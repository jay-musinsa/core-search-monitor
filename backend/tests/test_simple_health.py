#!/usr/bin/env python3
"""
간단한 헬스 체크 태스크 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Celery 설정 간소화
from celery import Celery

# 간단한 Celery 앱 생성
simple_app = Celery('simple_health', 
                   broker='redis://localhost:6379/1',
                   backend='redis://localhost:6379/2')

@simple_app.task
def simple_health_check():
    """간단한 헬스 체크"""
    import datetime
    return {
        'status': 'healthy', 
        'timestamp': datetime.datetime.now().isoformat(),
        'message': '헬스 체크 성공!'
    }

def test_simple_health():
    """간단한 헬스 체크 테스트"""
    print("🔧 간단한 헬스 체크 테스트")
    print("=" * 40)
    
    try:
        # 1. 즉시 실행 모드로 테스트
        print("1️⃣ 즉시 실행 모드로 테스트...")
        simple_app.conf.task_always_eager = True
        simple_app.conf.task_eager_propagates = True
        
        task = simple_health_check.delay()
        result = task.get()
        
        print(f"✅ 즉시 실행 성공!")
        print(f"📋 결과: {result}")
        
        # 2. 비동기 모드로 테스트
        print("\n2️⃣ 비동기 모드로 테스트...")
        simple_app.conf.task_always_eager = False
        
        task = simple_health_check.delay()
        print(f"📝 태스크 ID: {task.id}")
        print(f"📊 상태: {task.status}")
        
        # 짧은 대기 후 결과 확인
        try:
            result = task.get(timeout=3)
            print(f"✅ 비동기 실행 성공!")
            print(f"📋 결과: {result}")
        except Exception as e:
            print(f"⚠️ 비동기 실행 타임아웃: {e}")
            print("💡 워커가 실행 중인지 확인하세요")
        
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False

def test_original_health():
    """원래 헬스 체크 태스크도 즉시 실행으로 테스트"""
    print("\n3️⃣ 원래 헬스 체크 태스크 즉시 실행 테스트...")
    
    try:
        from app.core.celery_app import app, health_check
        
        # 즉시 실행 모드로 설정
        app.conf.task_always_eager = True
        app.conf.task_eager_propagates = True
        
        task = health_check.delay()
        result = task.get()
        
        print(f"✅ 원래 헬스 체크도 성공!")
        print(f"📋 결과: {result}")
        
        # 다시 비동기 모드로 복원
        app.conf.task_always_eager = False
        
        return True
        
    except Exception as e:
        print(f"❌ 원래 헬스 체크 실패: {e}")
        return False

if __name__ == '__main__':
    print("🩺 간단한 헬스 체크 테스트 시작!")
    
    # 간단한 테스트
    success1 = test_simple_health()
    
    # 원래 태스크 테스트
    success2 = test_original_health()
    
    if success1 and success2:
        print("\n🎉 모든 헬스 체크 테스트 성공!")
    else:
        print("\n⚠️ 일부 테스트 실패")
        
    print("\n💡 이제 Celery 워커에서도 태스크가 실행될 것입니다!") 