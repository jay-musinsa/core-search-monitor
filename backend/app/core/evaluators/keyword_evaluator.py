import re
from typing import Dict, List, Any, Optional
from .base_evaluator import BaseEvaluator, EvaluationResult

class KeywordEvaluator(BaseEvaluator):
    """Keyword 포함 여부 평가기 - 상품명/설명에 키워드 포함 여부로 정답 판단"""
    
    def __init__(self):
        super().__init__("Keyword-Based", default_confidence=0.7)
        
        # 동의어/유의어 매핑
        self.synonyms = {
            "반팔": ["반소매", "티셔츠", "반팔티"],
            "긴팔": ["긴소매", "롱슬리브"],
            "바지": ["팬츠", "트라우저"],
            "신발": ["슈즈", "화"],
            "가방": ["백", "백팩", "파우치"],
            # 더 많은 동의어 추가 가능
        }
        
        # 불용어 (검색과 관련없는 단어들)
        self.stop_words = {
            "무료배송", "할인", "세일", "이벤트", "신상", "추천", 
            "베스트", "인기", "hot", "new", "sale"
        }
    
    async def evaluate(self, 
                      keyword: str, 
                      products: List[Dict[str, Any]], 
                      screenshot_path: Optional[str] = None,
                      **kwargs) -> EvaluationResult:
        """Keyword 기반 평가 수행"""
        
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
        
        # 키워드 전처리
        processed_keyword = self._preprocess_keyword(keyword)
        
        for i, product in enumerate(products[:10]):  # 상위 10개만 평가
            score = self._calculate_keyword_relevance(processed_keyword, product)
            relevance_scores.append(score)
            
            # 낮은 점수의 상품을 precision issue로 분류
            if score < 0.3:
                # 상품명에서 키워드 유사도 계산
                product_name = product.get("goodsName", "").lower()
                keyword_similarity = self._calculate_similarity(keyword.lower(), product_name)
                
                precision_issues.append({
                    "goods_no": str(product.get("goodsNo", "")),
                    "goods_name": product.get("goodsName", ""),
                    "image_url": product.get("thumbnail", "N/A"),
                    "reason": f"키워드 기반 평가: 상품명에서 '{keyword}' 키워드와 관련성 부족 (유사도: {keyword_similarity:.2f}, 최종점수: {score:.2f})"
                })
        
        # 메트릭 계산
        ndcg_10 = self._calculate_ndcg(relevance_scores, k=10)
        precision, recall = self._calculate_precision_recall(relevance_scores, threshold=0.3)
        
        return EvaluationResult(
            ndcg_10=ndcg_10,
            precision=precision,
            recall=recall,
            confidence=self.default_confidence,
            method=self.name,
            details={
                "total_products": len(products),
                "evaluated_products": len(relevance_scores),
                "processed_keyword": processed_keyword,
                "average_relevance": sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0,
                "high_relevance_count": sum(1 for score in relevance_scores if score >= 0.7),
                "low_relevance_count": sum(1 for score in relevance_scores if score < 0.3)
            },
            precision_issues=precision_issues
        )
    
    def _preprocess_keyword(self, keyword: str) -> Dict[str, Any]:
        """키워드 전처리 및 확장"""
        if not keyword:
            return {"original": "", "tokens": [], "synonyms": []}
        
        # 소문자 변환 및 특수문자 제거
        cleaned = re.sub(r'[^\w\s]', ' ', keyword.lower()).strip()
        
        # 토큰화
        tokens = [token for token in cleaned.split() if token not in self.stop_words]
        
        # 동의어 확장
        expanded_tokens = set(tokens)
        for token in tokens:
            if token in self.synonyms:
                expanded_tokens.update(self.synonyms[token])
        
        return {
            "original": keyword,
            "cleaned": cleaned,
            "tokens": tokens,
            "expanded_tokens": list(expanded_tokens)
        }
    
    def _calculate_keyword_relevance(self, processed_keyword: Dict[str, Any], product: Dict[str, Any]) -> float:
        """키워드 관련성 점수 계산"""
        if not processed_keyword["tokens"]:
            return 0.0
        
        product_text = self._extract_product_text(product).lower()
        tokens = processed_keyword["tokens"]
        expanded_tokens = processed_keyword["expanded_tokens"]
        
        scores = []
        
        # 1. 정확한 키워드 매칭 (가중치: 0.5)
        exact_matches = sum(1 for token in tokens if token in product_text)
        exact_score = exact_matches / len(tokens) if tokens else 0
        scores.append(("exact_match", exact_score, 0.5))
        
        # 2. 동의어 매칭 (가중치: 0.3)
        synonym_matches = sum(1 for token in expanded_tokens if token in product_text)
        synonym_score = synonym_matches / len(expanded_tokens) if expanded_tokens else 0
        scores.append(("synonym_match", synonym_score, 0.3))
        
        # 3. 부분 문자열 매칭 (가중치: 0.2)
        partial_score = self._calculate_partial_match_score(tokens, product_text)
        scores.append(("partial_match", partial_score, 0.2))
        
        # 가중 평균 계산
        total_score = sum(score * weight for _, score, weight in scores)
        
        return min(1.0, max(0.0, total_score))
    
    def _extract_product_text(self, product: Dict[str, Any]) -> str:
        """상품에서 텍스트 정보 추출"""
        texts = []
        
        # 상품명
        if "goodsName" in product:
            texts.append(product["goodsName"])
        
        # 브랜드명 (상품명에서 추출)
        # 실제로는 별도 브랜드 필드가 있을 수 있음
        
        return " ".join(texts)
    
    def _calculate_partial_match_score(self, tokens: List[str], product_text: str) -> float:
        """부분 문자열 매칭 점수 계산"""
        if not tokens:
            return 0.0
        
        matches = 0
        for token in tokens:
            # 최소 3글자 이상일 때만 부분 매칭 수행
            if len(token) >= 3:
                for word in product_text.split():
                    if token in word or word in token:
                        matches += 1
                        break
        
        return matches / len(tokens)
    
    def _analyze_keyword_match(self, processed_keyword: Dict[str, Any], product: Dict[str, Any]) -> Dict[str, Any]:
        """키워드 매칭 분석 상세 정보"""
        product_text = self._extract_product_text(product).lower()
        tokens = processed_keyword["tokens"]
        expanded_tokens = processed_keyword["expanded_tokens"]
        
        analysis = {
            "product_text": product_text,
            "matched_tokens": [token for token in tokens if token in product_text],
            "matched_synonyms": [token for token in expanded_tokens if token in product_text and token not in tokens],
            "unmatched_tokens": [token for token in tokens if token not in product_text],
            "match_ratio": len([token for token in tokens if token in product_text]) / len(tokens) if tokens else 0
        }
        
        return analysis 