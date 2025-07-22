import re
from typing import Dict, List, Any, Optional
from .base_evaluator import BaseEvaluator, EvaluationResult

class RuleBasedEvaluator(BaseEvaluator):
    """Rule 기반 평가기 - 브랜드, 카테고리 등 메타데이터 기반"""
    
    def __init__(self):
        super().__init__("Rule-Based", default_confidence=0.9)
        
        # 카테고리 매핑 규칙
        self.category_rules = {
            "상의": ["티셔츠", "셔츠", "맨투맨", "후드", "니트", "가디건", "블라우스", "탑"],
            "하의": ["바지", "청바지", "팬츠", "스커트", "레깅스", "조거팬츠"],
            "아우터": ["자켓", "코트", "패딩", "점퍼", "가디건", "베스트"],
            "신발": ["운동화", "구두", "부츠", "샌들", "슬리퍼", "하이힐"],
            "가방": ["백팩", "토트백", "숄더백", "크로스백", "클러치"],
            "액세서리": ["모자", "벨트", "지갑", "시계", "목걸이", "귀걸이", "반지"]
        }
        
        # 브랜드 신뢰도 매핑 (예시)
        self.brand_trust_scores = {
            "나이키": 0.95,
            "아디다스": 0.95, 
            "무신사 스탠다드": 0.90,
            "유니클로": 0.85,
            # 더 많은 브랜드 추가 가능
        }
    
    async def evaluate(self, 
                      keyword: str, 
                      products: List[Dict[str, Any]], 
                      screenshot_path: Optional[str] = None,
                      **kwargs) -> EvaluationResult:
        """Rule 기반 평가 수행"""
        
        if not products:
            return EvaluationResult(
                ndcg_10=0.0,
                precision=0.0,
                recall=0.0,
                confidence=self.default_confidence,
                method=self.name,
                details={"reason": "상품 데이터가 없습니다."},
                precision_issues=[]
            )
        
        relevance_scores = []
        precision_issues = []
        
        for i, product in enumerate(products[:10]):  # 상위 10개만 평가
            score = self._calculate_product_relevance(keyword, product)
            relevance_scores.append(score)
            
            # 낮은 점수의 상품을 precision issue로 분류
            if score < 0.5:
                issues = []
                if self._calculate_keyword_match_score(keyword.lower(), product.get("goodsName", "").lower()) < 0.5:
                    issues.append("키워드 매칭 불일치")
                if self._calculate_category_match_score(keyword.lower(), product) < 0.5:
                    issues.append("카테고리 매칭 불일치")
                if self._calculate_brand_trust_score(product) < 0.7:
                    issues.append("브랜드 신뢰도 불일치")
                if self._calculate_price_reasonableness_score(product) < 0.8:
                    issues.append("가격 합리성 불일치")

                if issues:
                    precision_issues.append({
                        "goods_no": str(product.get("goodsNo", "")),
                        "goods_name": product.get("goodsName", ""),
                        "image_url": product.get("thumbnail", "N/A"),
                        "reason": f"규칙 기반 평가: {', '.join(issues)}"
                    })
        
        # 메트릭 계산
        ndcg_10 = self._calculate_ndcg(relevance_scores, k=10)
        precision, recall = self._calculate_precision_recall(relevance_scores)
        
        return EvaluationResult(
            ndcg_10=ndcg_10,
            precision=precision,
            recall=recall,
            confidence=self.default_confidence,
            method=self.name,
            details={
                "total_products": len(products),
                "evaluated_products": len(relevance_scores),
                "average_relevance": sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0,
                "rules_applied": ["category_matching", "brand_trust", "keyword_matching"]
            },
            precision_issues=precision_issues
        )
    
    def _calculate_product_relevance(self, keyword: str, product: Dict[str, Any]) -> float:
        """상품의 키워드 관련성 점수 계산"""
        score = 0.0
        weights = {
            "keyword_match": 0.4,
            "category_match": 0.3,
            "brand_trust": 0.2,
            "price_reasonableness": 0.1
        }
        
        product_name = product.get("goodsName", "").lower()
        keyword_lower = keyword.lower()
        
        # 1. 키워드 매칭 점수
        keyword_score = self._calculate_keyword_match_score(keyword_lower, product_name)
        score += keyword_score * weights["keyword_match"]
        
        # 2. 카테고리 매칭 점수
        category_score = self._calculate_category_match_score(keyword_lower, product)
        score += category_score * weights["category_match"]
        
        # 3. 브랜드 신뢰도 점수
        brand_score = self._calculate_brand_trust_score(product)
        score += brand_score * weights["brand_trust"]
        
        # 4. 가격 합리성 점수 (예시)
        price_score = self._calculate_price_reasonableness_score(product)
        score += price_score * weights["price_reasonableness"]
        
        return min(1.0, max(0.0, score))  # 0~1 범위로 제한
    
    def _calculate_keyword_match_score(self, keyword: str, product_name: str) -> float:
        """키워드 매칭 점수 계산"""
        if not keyword or not product_name:
            return 0.0
        
        # 완전 일치
        if keyword in product_name:
            return 1.0
        
        # 부분 일치 (키워드를 공백으로 분리해서 확인)
        keyword_parts = keyword.split()
        matches = sum(1 for part in keyword_parts if part in product_name)
        
        if matches > 0:
            return matches / len(keyword_parts)
        
        return 0.0
    
    def _calculate_category_match_score(self, keyword: str, product: Dict[str, Any]) -> float:
        """카테고리 매칭 점수 계산"""
        product_name = product.get("goodsName", "").lower()
        
        for category, terms in self.category_rules.items():
            # 키워드가 카테고리와 관련있는지 확인
            if any(term in keyword for term in terms):
                # 상품명이 같은 카테고리 용어를 포함하는지 확인
                if any(term in product_name for term in terms):
                    return 1.0
        
        return 0.5  # 기본 점수
    
    def _calculate_brand_trust_score(self, product: Dict[str, Any]) -> float:
        """브랜드 신뢰도 점수 계산"""
        product_name = product.get("goodsName", "")
        
        for brand, trust_score in self.brand_trust_scores.items():
            if brand.lower() in product_name.lower():
                return trust_score
        
        return 0.7  # 기본 브랜드 신뢰도
    
    def _calculate_price_reasonableness_score(self, product: Dict[str, Any]) -> float:
        """가격 합리성 점수 계산 (예시)"""
        # 실제로는 카테고리별 평균 가격과 비교하거나 
        # 가격대별 분포를 고려해야 함
        return 0.8  # 기본 점수
    
    def _get_rule_details(self, keyword: str, product: Dict[str, Any]) -> Dict[str, Any]:
        """Rule 적용 상세 정보 반환"""
        product_name = product.get("goodsName", "").lower()
        keyword_lower = keyword.lower()
        
        return {
            "keyword_match": self._calculate_keyword_match_score(keyword_lower, product_name),
            "category_match": self._calculate_category_match_score(keyword_lower, product),
            "brand_trust": self._calculate_brand_trust_score(product),
            "price_reasonableness": self._calculate_price_reasonableness_score(product)
        } 