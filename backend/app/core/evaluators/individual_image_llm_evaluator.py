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
        import hashlib
        
        # 키워드 기반 시드 생성 (일관된 결과를 위해)
        seed_str = f"{keyword}_{len(products)}"
        seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        # 키워드 복잡도에 따른 기본 성능 계산
        keyword_complexity = self._calculate_keyword_complexity(keyword)
        product_count = min(self.max_products, len(products))
        
        # 동적 메트릭 계산
        base_ndcg = 0.6 + (keyword_complexity * 0.3)  # 0.6 ~ 0.9
        base_precision = 0.5 + (keyword_complexity * 0.4)  # 0.5 ~ 0.9
        base_recall = 0.4 + (keyword_complexity * 0.4)  # 0.4 ~ 0.8
        
        # 상품 수에 따른 조정 (더 많은 상품 = 더 어려운 평가)
        product_difficulty = min(1.0, product_count / 50.0)  # 최대 50개 기준
        
        ndcg_10 = max(0.1, base_ndcg - (product_difficulty * 0.2))
        precision = max(0.1, base_precision - (product_difficulty * 0.15))
        recall = max(0.1, base_recall - (product_difficulty * 0.1))
        
        # 신뢰도는 Individual Image LLM의 특성상 높게 설정하되 동적 조정
        confidence = 0.85 + (keyword_complexity * 0.1) - (product_difficulty * 0.05)
        confidence = max(0.7, min(0.95, confidence))
        
        # 시뮬레이션용 precision_issues 생성
        precision_issues = []
        if products:
            # 정밀도에 따라 문제 상품 수 결정
            problem_ratio = 1.0 - precision
            problem_count = max(1, int(min(product_count, 10) * problem_ratio))
            
            if problem_count > 0:
                available_products = products[:min(product_count, 10)]
                problem_products = random.sample(available_products, min(problem_count, len(available_products)))
                
                for i, product in enumerate(problem_products):
                    # 다양한 시뮬레이션 이유 생성
                    reasons = [
                        f"상품 이미지가 '{keyword}' 키워드와 관련성 부족",
                        f"시각적 특성이 검색 의도와 불일치",
                        f"상품 카테고리가 '{keyword}' 검색과 맞지 않음",
                        f"이미지 품질이 정확한 판단을 어렵게 함"
                    ]
                    selected_reason = reasons[i % len(reasons)]
                    simulated_score = round(random.uniform(1.5, 2.8), 1)  # 3.0 미만 점수
                    
                    precision_issues.append({
                        "goods_no": str(product.get("goodsNo", "N/A")),
                        "goods_name": product.get("goodsName", "시뮬레이션 상품"),
                        "image_url": product.get("thumbnail", "N/A"),
                        "reason": f"개별 이미지 LLM 평가: {selected_reason} (관련성 점수: {simulated_score}/5.0, 시뮬레이션)"
                    })
        
        return EvaluationResult(
            method=self.name,
            ndcg_10=round(ndcg_10, 3),
            precision=round(precision, 3),
            recall=round(recall, 3),
            confidence=round(confidence, 3),
            details={
                "simulation": True,
                "total_products": len(products),
                "evaluated_products": product_count,
                "max_products": self.max_products,
                "keyword_complexity": keyword_complexity,
                "evaluation_method": "individual_image_analysis_simulation",
                "reasoning": f"키워드 '{keyword}'에 대한 {product_count}개 상품 개별 이미지 분석 시뮬레이션"
            },
            precision_issues=precision_issues
        )
    
    def _calculate_keyword_complexity(self, keyword: str) -> float:
        """키워드 복잡도 계산 (0.0 ~ 1.0)"""
        if not keyword:
            return 0.0
        
        complexity_factors = []
        
        # 1. 키워드 길이 (짧을수록 어려움)
        length_factor = min(1.0, len(keyword) / 10.0)
        complexity_factors.append(length_factor)
        
        # 2. 특수 문자/숫자 포함 여부
        special_chars = sum(1 for c in keyword if not c.isalnum() and c != ' ')
        special_factor = min(1.0, special_chars / 3.0)
        complexity_factors.append(special_factor)
        
        # 3. 영어/한글 혼용 여부
        has_korean = any('\uac00' <= c <= '\ud7af' for c in keyword)
        has_english = any(c.isalpha() and ord(c) < 128 for c in keyword)
        mixed_lang_factor = 0.8 if (has_korean and has_english) else 0.5
        complexity_factors.append(mixed_lang_factor)
        
        # 4. 공백으로 구분된 단어 수
        word_count = len(keyword.split())
        word_factor = min(1.0, word_count / 4.0)
        complexity_factors.append(word_factor)
        
        # 평균 복잡도 계산
        return sum(complexity_factors) / len(complexity_factors) 