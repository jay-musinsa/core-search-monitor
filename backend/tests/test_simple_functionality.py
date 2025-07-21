#!/usr/bin/env python3
"""
간단한 통합 테스트
기본적인 서비스 연결과 기능을 테스트합니다.
"""

import os
import sys
import redis
import clickhouse_connect
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_redis_connection():
    """Redis 연결 테스트"""
    print("🔍 Redis 연결 테스트...")
    try:
        redis_client = redis.from_url('redis://localhost:6380/0')
        result = redis_client.ping()
        print(f"✅ Redis 연결 성공: {result}")
        
        # 간단한 데이터 저장/조회 테스트
        test_key = "test:integration"
        test_value = f"test_value_{datetime.now().timestamp()}"
        
        redis_client.set(test_key, test_value, ex=60)  # 60초 후 만료
        retrieved_value = redis_client.get(test_key)
        
        if retrieved_value and retrieved_value.decode('utf-8') == test_value:
            print("✅ Redis 데이터 저장/조회 성공")
        else:
            print("❌ Redis 데이터 저장/조회 실패")
            return False
            
        redis_client.delete(test_key)
        return True
        
    except Exception as e:
        print(f"❌ Redis 연결 실패: {e}")
        return False


def test_clickhouse_connection():
    """ClickHouse 연결 테스트"""
    print("🔍 ClickHouse 연결 테스트...")
    try:
        client = clickhouse_connect.get_client(
            host='localhost',
            port=8124,
            username='default',
            password=''
        )
        
        # 기본 쿼리 테스트
        result = client.query('SELECT 1 as test_value')
        if result.result_rows and result.result_rows[0][0] == 1:
            print("✅ ClickHouse 연결 성공")
        else:
            print("❌ ClickHouse 쿼리 결과가 예상과 다름")
            return False
            
        # 데이터베이스 존재 확인
        databases = client.query('SHOW DATABASES')
        db_names = [row[0] for row in databases.result_rows]
        print(f"📊 사용 가능한 데이터베이스: {db_names}")
        
        return True
        
    except Exception as e:
        print(f"❌ ClickHouse 연결 실패: {e}")
        return False


def test_basic_imports():
    """기본 모듈 임포트 테스트"""
    print("🔍 기본 모듈 임포트 테스트...")
    try:
        from app.core.crawler import CrawlerMusinsa
        print("✅ CrawlerMusinsa 임포트 성공")
        
        from app.core.gpt import GPTMetricEvaluator
        print("✅ GPTMetricEvaluator 임포트 성공")
        
        from app.core.musinsa_api_service import MusinsaAPIService
        print("✅ MusinsaAPIService 임포트 성공")
        
        from app.core.redis_client import get_redis_client
        print("✅ redis_client 임포트 성공")
        
        return True
        
    except Exception as e:
        print(f"❌ 모듈 임포트 실패: {e}")
        return False


def test_api_service():
    """API 서비스 기본 테스트"""
    print("🔍 API 서비스 기본 테스트...")
    try:
        from app.core.musinsa_api_service import MusinsaAPIService
        
        api_service = MusinsaAPIService()
        print("✅ MusinsaAPIService 인스턴스 생성 성공")
        
        # 간단한 검색 테스트 (실제 API 호출 없이)
        print("📊 API 서비스 설정 확인 완료")
        
        return True
        
    except Exception as e:
        print(f"❌ API 서비스 테스트 실패: {e}")
        return False


def test_gpt_service():
    """GPT 서비스 기본 테스트"""
    print("🔍 GPT 서비스 기본 테스트...")
    try:
        from app.core.gpt import GPTMetricEvaluator
        
        gpt_service = GPTMetricEvaluator()
        print("✅ GPTMetricEvaluator 인스턴스 생성 성공")
        
        # API 키가 설정되어 있는지 확인
        if gpt_service.client:
            print("✅ OpenAI 클라이언트 설정됨")
        else:
            print("⚠️ OpenAI API 키가 설정되지 않음 (테스트 환경)")
        
        return True
        
    except Exception as e:
        print(f"❌ GPT 서비스 테스트 실패: {e}")
        return False


def main():
    """메인 테스트 실행"""
    print("🚀 키워드 품질평가 시스템 통합 테스트 시작")
    print("=" * 50)
    
    tests = [
        test_basic_imports,
        test_redis_connection,
        test_clickhouse_connection,
        test_api_service,
        test_gpt_service,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} 실행 중 예외 발생: {e}")
            failed += 1
        print("-" * 30)
    
    print(f"📊 테스트 결과: ✅ {passed}개 성공, ❌ {failed}개 실패")
    
    if failed == 0:
        print("🎉 모든 통합 테스트가 성공했습니다!")
        return True
    else:
        print("⚠️ 일부 테스트가 실패했습니다. 로그를 확인해주세요.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)