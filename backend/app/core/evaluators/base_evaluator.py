from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class EvaluationResult:
    """평가 결과를 담는 데이터 클래스"""
    ndcg_10: float
    precision: float
    recall: float
    confidence: float  # 평가 신뢰도 (0.0 ~ 1.0)
    method: str  # 평가 방법명
    details: Dict[str, Any]  # 상세 정보
    precision_issues: List[Dict[str, Any]] = None  # Precision 문제 상품들
    
    def __post_init__(self):
        if self.precision_issues is None:
            self.precision_issues = []

class BaseEvaluator(ABC):
    """모든 평가기의 기본 인터페이스"""
    
    def __init__(self, name: str, default_confidence: float = 0.8):
        self.name = name
        self.default_confidence = default_confidence
    
    @abstractmethod
    async def evaluate(self, 
                      keyword: str, 
                      products: List[Dict[str, Any]], 
                      screenshot_path: Optional[str] = None,
                      **kwargs) -> EvaluationResult:
        """
        검색 결과를 평가합니다.
        
        Args:
            keyword: 검색 키워드
            products: 상품 리스트 (API 데이터)
            screenshot_path: 스크린샷 경로 (선택적)
            **kwargs: 추가 파라미터
            
        Returns:
            EvaluationResult: 평가 결과
        """
        pass
    
    def _calculate_ndcg(self, relevance_scores: List[float], k: int = 10) -> float:
        """NDCG@K 계산"""
        if not relevance_scores or k <= 0:
            return 0.0
            
        # 실제 순서의 DCG 계산
        dcg = self._calculate_dcg(relevance_scores[:k])
        
        # 이상적인 순서의 DCG 계산 (내림차순 정렬)
        ideal_scores = sorted(relevance_scores, reverse=True)[:k]
        idcg = self._calculate_dcg(ideal_scores)
        
        if idcg == 0:
            return 0.0
            
        return dcg / idcg
    
    def _calculate_dcg(self, scores: List[float]) -> float:
        """DCG (Discounted Cumulative Gain) 계산"""
        import math
        dcg = 0.0
        for i, score in enumerate(scores):
            if i == 0:
                dcg += score
            else:
                dcg += score / math.log2(i + 1)
        return dcg
    
    def _calculate_precision_recall(self, relevance_scores: List[float], threshold: float = 0.5) -> tuple:
        """Precision과 Recall 계산"""
        if not relevance_scores:
            return 0.0, 0.0
            
        # 임계값 이상을 관련 있는 것으로 판단
        relevant_items = [1 if score >= threshold else 0 for score in relevance_scores]
        
        # Precision: 검색된 결과 중 관련 있는 비율
        total_retrieved = len(relevant_items)
        relevant_retrieved = sum(relevant_items)
        precision = relevant_retrieved / total_retrieved if total_retrieved > 0 else 0.0
        
        # Recall: 전체 관련 있는 항목 중 검색된 비율 (여기서는 precision과 동일하게 계산)
        # 실제로는 전체 데이터베이스의 관련 항목 수를 알아야 하지만, 
        # 검색 결과만으로는 추정할 수밖에 없음
        recall = precision  # 단순화된 계산
        
        return precision, recall 