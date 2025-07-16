"""
무신사 API 서비스
무신사 검색 API를 호출하여 상품 데이터를 가져오는 서비스
"""

import requests
import json
import urllib.parse
from typing import List, Dict, Optional


class MusinsaAPIService:
    def __init__(self):
        self.base_url = "https://api.musinsa.com/api2/dp/v1/plp/goods"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Referer': 'https://www.musinsa.com/',
            'Origin': 'https://www.musinsa.com'
        }

    def fetch_search_data(self, keyword: str, page: int = 1, size: int = 60) -> Dict:
        """무신사 검색 API 호출하여 상품 데이터 가져오기"""
        try:
            # URL 인코딩
            encoded_keyword = urllib.parse.quote(keyword)
            
            params = {
                'gf': 'A',
                'keyword': encoded_keyword,
                'sortCode': 'POPULAR',
                'page': page,
                'size': size,
                'caller': 'SEARCH'
            }
            
            print(f"[무신사 API] 검색 요청: {keyword}, 페이지: {page}, 크기: {size}")
            
            response = requests.get(self.base_url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # API 응답 로그 출력
            self._log_api_response(data, keyword, page)
            
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"[무신사 API] API 호출 실패: {e}")
            return {}
        except json.JSONDecodeError as e:
            print(f"[무신사 API] JSON 파싱 실패: {e}")
            return {}
        except Exception as e:
            print(f"[무신사 API] 처리 중 예외: {e}")
            return {}

    def fetch_100_items(self, keyword: str) -> List[Dict]:
        """100개의 상품을 가져오기 위해 페이지네이션 처리"""
        all_items = []
        page = 1
        items_per_page = 60  # API에서 한 번에 가져올 수 있는 최대 개수
        
        print(f"[무신사 API] 100개 상품 수집 시작: {keyword}")
        
        while len(all_items) < 100:
            data = self.fetch_search_data(keyword, page=page, size=items_per_page)
            
            if not data or 'data' not in data or 'list' not in data['data']:
                print(f"[무신사 API] 페이지 {page}에서 데이터를 가져올 수 없습니다.")
                break
            
            items = data['data']['list']
            if not items:
                print(f"[무신사 API] 페이지 {page}에 더 이상 상품이 없습니다.")
                break
            
            all_items.extend(items)
            print(f"[무신사 API] 페이지 {page} 완료: {len(items)}개 상품 추가, 총 {len(all_items)}개")
            
            # 다음 페이지가 있는지 확인
            pagination = data['data'].get('pagination', {})
            if not pagination.get('hasNext', False):
                print(f"[무신사 API] 더 이상 다음 페이지가 없습니다.")
                break
            
            page += 1
            
            # 무한 루프 방지
            if page > 10:
                print(f"[무신사 API] 최대 페이지 수(10)에 도달했습니다.")
                break
        
        # 100개로 제한
        result_items = all_items[:100]
        print(f"[무신사 API] 최종 수집 완료: {len(result_items)}개 상품")
        
        # 수집된 상품들의 요약 정보 출력
        self._log_summary(result_items)
        
        return result_items

    def _log_api_response(self, data: Dict, keyword: str, page: int) -> None:
        """API 응답 로그 출력"""
        print(f"[무신사 API] 검색 응답 성공: {keyword}")
        print(f"[무신사 API] 총 상품 수: {data.get('data', {}).get('pagination', {}).get('totalCount', 0)}")
        print(f"[무신사 API] 현재 페이지: {data.get('data', {}).get('pagination', {}).get('page', 0)}")
        print(f"[무신사 API] 상품 리스트 개수: {len(data.get('data', {}).get('list', []))}")

    def _log_summary(self, items: List[Dict]) -> None:
        """수집된 상품들의 요약 정보 출력"""
        if not items:
            return
            
        print(f"[무신사 API] 수집된 상품 요약:")
        print(f"[무신사 API]   - 총 상품 수: {len(items)}")
        print(f"[무신사 API]   - 브랜드 수: {len(set(item.get('brandName', '') for item in items))}")
        
       
    def get_product_details(self, goods_no: int) -> Optional[Dict]:
        """특정 상품의 상세 정보 가져오기"""
        try:
            url = f"https://api.musinsa.com/api2/dp/v1/goods/{goods_no}"
            
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            print(f"[무신사 API] 상품 상세 정보 가져오기 성공: {goods_no}")
            
            return data
            
        except Exception as e:
            print(f"[무신사 API] 상품 상세 정보 가져오기 실패: {goods_no}, 오류: {e}")
            return None 