#!/usr/bin/env python3
"""
크롤러 테스트 스크립트
"""

import asyncio
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.crawler import CrawlerMusinsa, Crawler29CM

def test_musinsa_crawler():
    """무신사 크롤러 테스트"""
    print("=== 무신사 크롤러 테스트 시작 ===")
    crawler = CrawlerMusinsa()
    
    try:
        result = crawler.capture_screenshot("노랑색 반팔티")
        print(f"무신사 크롤러 결과: {result}")
        return result
    except Exception as e:
        print(f"무신사 크롤러 테스트 실패: {e}")
        import traceback
        print(f"상세 에러: {traceback.format_exc()}")
        return None

def test_29cm_crawler():
    """29CM 크롤러 테스트"""
    print("\n=== 29CM 크롤러 테스트 시작 ===")
    crawler = Crawler29CM()
    
    try:
        result = crawler.capture_screenshot("노랑색 반팔티")
        print(f"29CM 크롤러 결과: {result}")
        return result
    except Exception as e:
        print(f"29CM 크롤러 테스트 실패: {e}")
        import traceback
        print(f"상세 에러: {traceback.format_exc()}")
        return None

def main():
    """메인 테스트 함수"""
    print("크롤러 테스트 시작...")
    
    # 무신사 크롤러 테스트
    musinsa_result = test_musinsa_crawler()
    
    # 29CM 크롤러 테스트
    cm29_result = test_29cm_crawler()
    
    print("\n=== 테스트 결과 요약 ===")
    print(f"무신사: {'성공' if musinsa_result else '실패'}")
    print(f"29CM: {'성공' if cm29_result else '실패'}")
    
    if musinsa_result and cm29_result:
        print("모든 크롤러 테스트 성공!")
    else:
        print("일부 크롤러 테스트 실패!")

if __name__ == "__main__":
    main() 