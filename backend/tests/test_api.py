#!/usr/bin/env python3
"""
무신사 API 서비스 테스트 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.musinsa_api_service import MusinsaAPIService
from app.core.metrics import metrics_manager
import asyncio

def test_musinsa_api_service():
    """무신사 API 서비스 테스트"""
    print("=== 무신사 API 서비스 테스트 시작 ===")
    
    api_service = MusinsaAPIService()
    
    # 테스트 키워드들
    test_keywords = ["반팔", "티셔츠"]
    
    for keyword in test_keywords:
        print(f"\n--- 키워드: {keyword} ---")
        try:
            # 100개 상품 가져오기
            items = api_service.fetch_100_items(keyword)
            print(f"성공적으로 {len(items)}개 상품을 가져왔습니다.")
            
            if items:
                # 첫 번째 상품 정보 출력
                first_item = items[0]
                print(f"첫 번째 상품: {first_item.get('goodsName', 'N/A')}")
                print(f"브랜드: {first_item.get('brandName', 'N/A')}")
                print(f"가격: {first_item.get('price', 0):,}원")
                print(f"할인율: {first_item.get('saleRate', 0)}%")
            
        except Exception as e:
            print(f"오류 발생: {e}")
    
    print("\n=== API 서비스 테스트 완료 ===")

async def test_metrics_manager():
    """메트릭 매니저 테스트"""
    print("\n=== 메트릭 매니저 테스트 시작 ===")
    
    test_keyword = "반팔"
    
    try:
        print(f"키워드 '{test_keyword}' 처리 시작...")
        result = await metrics_manager.process_keyword(test_keyword)
        
        if "error" in result:
            print(f"처리 실패: {result['error']}")
        else:
            print(f"처리 성공: {result}")
            
            # 메트릭 조회
            metrics = metrics_manager.get_metrics(test_keyword)
            print(f"저장된 메트릭: {metrics}")
            
    except Exception as e:
        print(f"메트릭 매니저 테스트 오류: {e}")
    
    print("=== 메트릭 매니저 테스트 완료 ===")

async def main():
    """메인 테스트 함수"""
    # 1. API 서비스 테스트
    test_musinsa_api_service()
    
    # 2. 메트릭 매니저 테스트
    await test_metrics_manager()

if __name__ == "__main__":
    asyncio.run(main()) 