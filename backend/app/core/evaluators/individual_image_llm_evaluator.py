"""
Individual Image LLM 평가기
검색 API 응답의 각 상품 이미지를 개별적으로 LLM에게 평가받는 평가기
"""

import asyncio
import base64
import requests
from typing import Dict, List, Any, Optional
from openai import OpenAI
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import config
from .base_evaluator import BaseEvaluator, EvaluationResult


class IndividualImageLLMEvaluator(BaseEvaluator):
    def __init__(self, max_products: int = 50):
        super().__init__("Individual-Image-LLM")
        self.description = "각 상품 이미지를 개별적으로 LLM에게 평가받는 평가기"
        self.max_products = max_products  # 평가할 최대 상품 수
        
        # OpenAI 클라이언트 초기화
        api_key = config.get_openai_api_key()
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None
            print(f"[{self.name}] 경고: OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
    
    async def evaluate(self, keyword: str, products: List[Dict], screenshot_path: str = None) -> EvaluationResult:
        """개별 이미지 LLM 평가 실행"""
        print(f"[{self.name}] {keyword} 개별 이미지 평가 시작 (상품 수: {len(products)})")
        
        if not self.client:
            print(f"[{self.name}] OpenAI API 키가 없어 시뮬레이션 결과 반환")
            return self._create_simulation_result(keyword, products)
        
        if not products:
            print(f"[{self.name}] 평가할 상품이 없습니다")
            return EvaluationResult(
                method=self.name,
                ndcg_10=0.0,
                precision=0.0,
                recall=0.0,
                confidence=0.0,
                details={"error": "평가할 상품이 없습니다"},
                precision_issues=[]
            )
        
        try:
            # 각 상품 이미지를 개별적으로 평가
            individual_evaluations = []
            relevant_count = 0
            precision_issues = []
            
            # 병렬 처리를 위한 세마포어 (동시 요청 수 제한)
            semaphore = asyncio.Semaphore(3)  # 최대 3개 동시 요청
            
            async def evaluate_single_product(product, rank):
                async with semaphore:
                    return await self._evaluate_single_product(keyword, product, rank)
            
            # 설정된 개수만큼 상품 평가 (기본 50개)
            top_products = products[:self.max_products]
            print(f"[{self.name}] 상위 {len(top_products)}개 상품 평가 시작 (최대 {self.max_products}개)")
            
            tasks = [
                evaluate_single_product(product, rank + 1) 
                for rank, product in enumerate(top_products)
            ]
            
            individual_evaluations = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 결과 집계
            valid_evaluations = []
            for i, eval_result in enumerate(individual_evaluations):
                if isinstance(eval_result, Exception):
                    print(f"[{self.name}] 상품 {i+1} 평가 실패: {eval_result}")
                    valid_evaluations.append({
                        "rank": i + 1,
                        "relevant": False,
                        "relevance_score": 0.0,
                        "reason": f"평가 실패: {str(eval_result)}"
                    })
                else:
                    valid_evaluations.append(eval_result)
                    if eval_result["relevant"]:
                        relevant_count += 1
                    else:
                        # 관련성이 낮은 상품을 precision_issues에 추가
                        product = top_products[i]
                        reason_detail = eval_result.get('reason', '관련성 없음')
                        relevance_score = eval_result.get('relevance_score', 0.0)
                        
                        precision_issues.append({
                            "goods_no": str(product.get("goodsNo", "N/A")),
                            "goods_name": product.get("goodsName", "N/A"),
                            "image_url": product.get("thumbnail", "N/A"),
                            "reason": f"개별 이미지 LLM 평가: {reason_detail} (관련성 점수: {relevance_score:.2f}/5.0)"
                        })
            
            # 메트릭 계산
            # NDCG@10은 상위 10개만 사용
            ndcg_evaluations = valid_evaluations[:10]
            ndcg_10 = self._calculate_ndcg_10(ndcg_evaluations)
            
            # Precision과 Recall은 전체 평가 결과 사용
            precision = relevant_count / len(valid_evaluations) if valid_evaluations else 0.0
            # Recall: 전체 평가한 상품 중 관련성 있는 비율 (이상적으로는 모두 관련성 있어야 함)
            recall = relevant_count / len(valid_evaluations) if valid_evaluations else 0.0
            
            # 신뢰도 계산 (평가 성공률 기반)
            success_rate = len([e for e in valid_evaluations if "평가 실패" not in e.get("reason", "")]) / len(valid_evaluations)
            confidence = 0.9 * success_rate  # 개별 이미지 평가는 높은 신뢰도
            
            print(f"[{self.name}] {keyword} 평가 완료: NDCG={ndcg_10:.3f}, Precision={precision:.3f}, 신뢰도={confidence:.3f}")
            
            return EvaluationResult(
                method=self.name,
                ndcg_10=ndcg_10,
                precision=precision,
                recall=recall,
                confidence=confidence,
                details={
                    "total_products": len(products),
                    "evaluated_products": len(valid_evaluations),
                    "relevant_products": relevant_count,
                    "individual_evaluations": valid_evaluations,
                    "evaluation_method": "individual_image_analysis"
                },
                precision_issues=precision_issues
            )
            
        except Exception as e:
            print(f"[{self.name}] {keyword} 평가 실패: {e}")
            return EvaluationResult(
                method=self.name,
                ndcg_10=0.0,
                precision=0.0,
                recall=0.0,
                confidence=0.0,
                details={"error": str(e)},
                precision_issues=[]
            )
    
    async def _evaluate_single_product(self, keyword: str, product: Dict, rank: int) -> Dict:
        """개별 상품 이미지를 LLM으로 평가"""
        try:
            image_url = product.get("thumbnail", "")
            goods_name = product.get("goodsName", "")
            goods_no = product.get("goodsNo", "")
            
            if not image_url or image_url == "N/A":
                return {
                    "rank": rank,
                    "goods_no": goods_no,
                    "goods_name": goods_name,
                    "relevant": False,
                    "relevance_score": 0.0,
                    "reason": "이미지 URL이 없습니다"
                }
            
            # 이미지 다운로드 및 base64 인코딩
            base64_image = await self._download_and_encode_image(image_url)
            if not base64_image:
                return {
                    "rank": rank,
                    "goods_no": goods_no,
                    "goods_name": goods_name,
                    "relevant": False,
                    "relevance_score": 0.0,
                    "reason": "이미지 다운로드 실패"
                }
            
            # LLM에게 개별 상품 평가 요청
            prompt = f"""
다음 상품이 검색 키워드 "{keyword}"와 얼마나 관련성이 있는지 평가해주세요.

상품 정보:
- 상품명: {goods_name}
- 상품번호: {goods_no}
- 순위: {rank}

평가 기준:
1. 이미지의 상품이 키워드와 직접적으로 관련이 있는가?
2. 상품명과 이미지가 일치하는가?
3. 검색 의도에 부합하는가?

응답은 반드시 다음 JSON 형식으로 해주세요:
{{
    "relevant": true/false,
    "relevance_score": 0.0-1.0,
    "reason": "평가 이유 (한국어로 간단히)"
}}
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300
            )
            
            # 응답 파싱
            content = response.choices[0].message.content.strip()
            
            # JSON 파싱
            try:
                if content.startswith("```json"):
                    content = content[7:-3]
                elif content.startswith("```"):
                    content = content[3:-3]
                
                result = json.loads(content)
                
                return {
                    "rank": rank,
                    "goods_no": goods_no,
                    "goods_name": goods_name,
                    "relevant": result.get("relevant", False),
                    "relevance_score": float(result.get("relevance_score", 0.0)),
                    "reason": result.get("reason", "평가 완료")
                }
                
            except json.JSONDecodeError as e:
                print(f"[{self.name}] JSON 파싱 실패 (상품 {goods_no}): {e}")
                return {
                    "rank": rank,
                    "goods_no": goods_no,
                    "goods_name": goods_name,
                    "relevant": False,
                    "relevance_score": 0.0,
                    "reason": "LLM 응답 파싱 실패"
                }
        
        except Exception as e:
            print(f"[{self.name}] 개별 상품 평가 실패 (상품 {product.get('goodsNo', 'Unknown')}): {e}")
            return {
                "rank": rank,
                "goods_no": product.get("goodsNo", ""),
                "goods_name": product.get("goodsName", ""),
                "relevant": False,
                "relevance_score": 0.0,
                "reason": f"평가 오류: {str(e)}"
            }
    
    async def _download_and_encode_image(self, image_url: str) -> Optional[str]:
        """이미지를 다운로드하고 base64로 인코딩"""
        try:
            # 동기적 요청을 비동기로 처리
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.get(image_url, timeout=10)
            )
            
            if response.status_code == 200:
                return base64.b64encode(response.content).decode('utf-8')
            else:
                print(f"[{self.name}] 이미지 다운로드 실패: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"[{self.name}] 이미지 다운로드 오류: {e}")
            return None
    
    def _calculate_ndcg_10(self, evaluations: List[Dict]) -> float:
        """NDCG@10 계산"""
        if not evaluations:
            return 0.0
        
        # relevance_score 기반으로 DCG 계산
        dcg = 0.0
        for i, eval_result in enumerate(evaluations):
            relevance = eval_result.get("relevance_score", 0.0)
            if i == 0:
                dcg += relevance
            else:
                dcg += relevance / (i + 1) ** 0.5  # log2(i+2) 대신 sqrt(i+1) 사용
        
        # IDCG 계산 (이상적인 순서)
        ideal_relevances = sorted([e.get("relevance_score", 0.0) for e in evaluations], reverse=True)
        idcg = 0.0
        for i, relevance in enumerate(ideal_relevances):
            if i == 0:
                idcg += relevance
            else:
                idcg += relevance / (i + 1) ** 0.5
        
        return dcg / idcg if idcg > 0 else 0.0
    
    def _create_simulation_result(self, keyword: str, products: List[Dict]) -> EvaluationResult:
        """시뮬레이션 결과 생성 (API 키가 없을 때)"""
        import random
        
        # 시뮬레이션용 precision_issues 생성
        precision_issues = []
        if products:
            # 랜덤하게 몇 개 상품을 문제 상품으로 선정
            problem_count = min(3, len(products) // 3)
            problem_products = random.sample(products[:10], problem_count)
            
            for product in problem_products:
                precision_issues.append({
                    "goods_no": str(product.get("goodsNo", "N/A")),
                    "goods_name": product.get("goodsName", "시뮬레이션 상품"),
                    "image_url": product.get("thumbnail", "N/A"),
                    "reason": "개별 이미지 분석 결과 관련성 낮음 (시뮬레이션)"
                })
        
        return EvaluationResult(
            method=self.name,
            ndcg_10=0.85,  # 시뮬레이션 값
            precision=0.80,
            recall=0.75,
            confidence=0.90,  # 개별 이미지 분석은 높은 신뢰도
            details={
                "simulation": True,
                "total_products": len(products),
                "evaluated_products": min(10, len(products)),
                "evaluation_method": "individual_image_analysis_simulation"
            },
            precision_issues=precision_issues
        ) 