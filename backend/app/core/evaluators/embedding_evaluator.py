import os
import numpy as np
from typing import Dict, List, Any, Optional
from .base_evaluator import BaseEvaluator, EvaluationResult

class EmbeddingEvaluator(BaseEvaluator):
    """Embedding 유사도 평가기 - BERT, CLIP 등을 사용한 텍스트/이미지 임베딩 유사도 측정"""
    
    def __init__(self, model_type: str = "sentence-transformers"):
        super().__init__(f"Embedding-{model_type}", default_confidence=0.85)
        self.model_type = model_type
        self.text_model = None
        self.image_model = None
        
        # 모델 초기화
        self._initialize_models()
    
    def _initialize_models(self):
        """임베딩 모델 초기화"""
        try:
            if self.model_type == "sentence-transformers":
                # SentenceTransformers 사용
                from sentence_transformers import SentenceTransformer
                self.text_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
                print(f"[{self.name}] SentenceTransformers 모델 로드 완료")
                
            elif self.model_type == "clip":
                # CLIP 모델 사용 (텍스트 + 이미지)
                try:
                    import clip
                    import torch
                    self.clip_model, self.clip_preprocess = clip.load("ViT-B/32", device="cpu")
                    print(f"[{self.name}] CLIP 모델 로드 완료")
                except ImportError:
                    print(f"[{self.name}] CLIP 라이브러리가 설치되지 않음. sentence-transformers로 폴백")
                    from sentence_transformers import SentenceTransformer
                    self.text_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
                    
        except ImportError as e:
            print(f"[{self.name}] 임베딩 모델 로드 실패: {e}")
            print(f"[{self.name}] 시뮬레이션 모드로 동작합니다.")
    
    async def evaluate(self, 
                      keyword: str, 
                      products: List[Dict[str, Any]], 
                      screenshot_path: Optional[str] = None,
                      **kwargs) -> EvaluationResult:
        """Embedding 기반 평가 수행"""
        
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
        
        if not self.text_model and self.model_type != "clip":
            return await self._generate_simulation_result(keyword, products)
        
        try:
            # 키워드 임베딩 생성
            keyword_embedding = await self._get_text_embedding(keyword)
            
            relevance_scores = []
            precision_issues = []
            
            for i, product in enumerate(products[:10]):  # 상위 10개만 평가
                # 상품 텍스트 임베딩 생성
                product_text = self._extract_product_text(product)
                product_embedding = await self._get_text_embedding(product_text)
                
                # 유사도 계산
                similarity = self._calculate_cosine_similarity(keyword_embedding, product_embedding)
                relevance_scores.append(similarity)
                
                # 낮은 점수의 상품을 precision issue로 분류
                if similarity < 0.4:
                    precision_issues.append({
                        "goods_no": str(product.get("goodsNo", "")),
                        "goods_name": product.get("goodsName", ""),
                        "image_url": product.get("thumbnail", "N/A"),
                        "reason": f"임베딩 기반 평가: 의미적 유사도 낮음 (임베딩 유사도: {similarity:.3f}, 임계값: 0.4 미만)"
                    })
            
            # 메트릭 계산
            ndcg_10 = self._calculate_ndcg(relevance_scores, k=10)
            precision, recall = self._calculate_precision_recall(relevance_scores, threshold=0.5)
            
            return EvaluationResult(
                ndcg_10=ndcg_10,
                precision=precision,
                recall=recall,
                confidence=self.default_confidence,
                method=self.name,
                details={
                    "model_type": self.model_type,
                    "total_products": len(products),
                    "evaluated_products": len(relevance_scores),
                    "average_similarity": sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0,
                    "high_similarity_count": sum(1 for score in relevance_scores if score >= 0.7),
                    "low_similarity_count": sum(1 for score in relevance_scores if score < 0.3)
                },
                precision_issues=precision_issues
            )
            
        except Exception as e:
            print(f"[{self.name}] 평가 실패: {e}")
            return await self._generate_simulation_result(keyword, products)
    
    async def _get_text_embedding(self, text: str) -> np.ndarray:
        """텍스트 임베딩 생성"""
        if not text:
            return np.zeros(384)  # 기본 차원
        
        try:
            if self.model_type == "sentence-transformers" and self.text_model:
                embedding = self.text_model.encode(text)
                return np.array(embedding)
                
            elif self.model_type == "clip" and hasattr(self, 'clip_model'):
                import torch
                import clip
                
                text_tokens = clip.tokenize([text])
                with torch.no_grad():
                    text_features = self.clip_model.encode_text(text_tokens)
                    text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                
                return text_features.numpy()[0]
            
            else:
                # 폴백: 간단한 TF-IDF 기반 벡터화
                return self._simple_text_vectorize(text)
                
        except Exception as e:
            print(f"[{self.name}] 텍스트 임베딩 생성 실패: {e}")
            return self._simple_text_vectorize(text)
    
    def _simple_text_vectorize(self, text: str) -> np.ndarray:
        """간단한 텍스트 벡터화 (폴백)"""
        # 매우 단순한 문자 기반 해싱 벡터화
        vector = np.zeros(384)
        for i, char in enumerate(text.lower()[:100]):
            idx = hash(char) % 384
            vector[idx] += 1
        
        # 정규화
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
            
        return vector
    
    def _calculate_cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """코사인 유사도 계산"""
        try:
            # 벡터 차원이 다른 경우 조정
            if len(vec1) != len(vec2):
                min_dim = min(len(vec1), len(vec2))
                vec1 = vec1[:min_dim]
                vec2 = vec2[:min_dim]
            
            # 코사인 유사도 계산
            dot_product = np.dot(vec1, vec2)
            norm_vec1 = np.linalg.norm(vec1)
            norm_vec2 = np.linalg.norm(vec2)
            
            if norm_vec1 == 0 or norm_vec2 == 0:
                return 0.0
            
            similarity = dot_product / (norm_vec1 * norm_vec2)
            
            # -1 ~ 1 범위를 0 ~ 1로 변환
            return (similarity + 1) / 2
            
        except Exception as e:
            print(f"[{self.name}] 유사도 계산 실패: {e}")
            return 0.0
    
    def _extract_product_text(self, product: Dict[str, Any]) -> str:
        """상품에서 텍스트 정보 추출"""
        texts = []
        
        # 상품명
        if "goodsName" in product:
            texts.append(product["goodsName"])
        
        # 추가 텍스트 필드들 (있는 경우)
        text_fields = ["brandName", "categoryName", "description"]
        for field in text_fields:
            if field in product and product[field]:
                texts.append(str(product[field]))
        
        return " ".join(texts)
    
    async def _generate_simulation_result(self, keyword: str, products: List[Dict[str, Any]]) -> EvaluationResult:
        """시뮬레이션 결과 생성"""
        # 간단한 키워드 매칭 기반 시뮬레이션
        relevance_scores = []
        precision_issues = []
        
        keyword_lower = keyword.lower()
        
        for product in products[:10]:
            product_text = self._extract_product_text(product).lower()
            
            # 단순 키워드 포함 여부로 유사도 추정
            if keyword_lower in product_text:
                score = 0.8 + np.random.normal(0, 0.1)  # 노이즈 추가
            else:
                score = 0.3 + np.random.normal(0, 0.1)
            
            score = max(0.0, min(1.0, score))  # 0~1 범위로 제한
            relevance_scores.append(score)
            
            if score < 0.5:
                precision_issues.append({
                    "goods_no": product.get("goodsNo", ""),
                    "goods_name": product.get("goodsName", ""),
                    "image_url": product.get("thumbnail", "N/A"),
                    "reason": f"시뮬레이션 유사도가 낮음 ({score:.3f})",
                    "similarity_score": score,
                    "embedding_model": f"{self.model_type} (simulation)"
                })
        
        ndcg_10 = self._calculate_ndcg(relevance_scores, k=10)
        precision, recall = self._calculate_precision_recall(relevance_scores, threshold=0.5)
        
        return EvaluationResult(
            ndcg_10=ndcg_10,
            precision=precision,
            recall=recall,
            confidence=0.4,  # 시뮬레이션은 신뢰도 낮음
            method=self.name,
            details={
                "simulation": True,
                "model_type": self.model_type,
                "reason": "임베딩 모델이 로드되지 않아 시뮬레이션으로 동작",
                "total_products": len(products),
                "average_similarity": sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
            },
            precision_issues=precision_issues
        ) 