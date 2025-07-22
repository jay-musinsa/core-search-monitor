"""
종합 평가기 (Composite Evaluator)
여러 평가 방법을 조합하여 최종 점수를 계산하는 평가기
"""

import asyncio
from typing import Dict, List, Any
from .base_evaluator import BaseEvaluator, EvaluationResult
from .rule_based_evaluator import RuleBasedEvaluator
from .keyword_evaluator import KeywordEvaluator
from .llm_evaluator import LLMEvaluator
from .embedding_evaluator import EmbeddingEvaluator
from .individual_image_llm_evaluator import IndividualImageLLMEvaluator


class CompositeEvaluator(BaseEvaluator):
    def __init__(self, enable_individual_image_llm: bool = False, evaluator_config: Dict = None):
        super().__init__("Composite")
        self.description = "다중 평가 시스템을 통한 종합 평가"
        
        # 기본 평가기들 (항상 활성화)
        self.rule_based = RuleBasedEvaluator()
        self.keyword = KeywordEvaluator()
        self.llm = LLMEvaluator()
        self.embedding = EmbeddingEvaluator()
        
        # 개별 이미지 LLM 평가기 (옵션)
        self.enable_individual_image_llm = enable_individual_image_llm
        if enable_individual_image_llm:
            # 설정에서 max_products 값 읽기 (기본값: 50)
            max_products = 50
            if evaluator_config and 'individual_image_llm' in evaluator_config:
                config = evaluator_config['individual_image_llm']
                max_products = config.get('max_products', 50)
                print(f"[{self.name}] 로드된 Individual Image LLM 설정: {config}")
            else:
                print(f"[{self.name}] Individual Image LLM 설정을 찾을 수 없음, 기본값 사용: max_products={max_products}")
            
            self.individual_image_llm = IndividualImageLLMEvaluator(max_products=max_products)
            print(f"[{self.name}] Individual Image LLM 평가기 활성화됨 (최대 {max_products}개 상품)")
        else:
            self.individual_image_llm = None
        
        # 기본 가중치 설정
        self.weights = {
            'rule_based': 0.2,
            'keyword': 0.2,
            'llm': 0.4,
            'embedding': 0.2,
            'individual_image_llm': 0.3  # 활성화 시 가중치 재조정됨
        }
    
    async def evaluate(self, keyword: str, products: List[Dict], screenshot_path: str = None) -> EvaluationResult:
        """종합 평가 실행"""
        print(f"[{self.name}] {keyword} 종합 평가 시작")
        
        if not products and not screenshot_path:
            return EvaluationResult(
                method=self.name,
                ndcg_10=0.0,
                precision=0.0,
                recall=0.0,
                confidence=0.0,
                details={"error": "평가할 데이터가 없습니다"},
                precision_issues=[]
            )
        
        try:
            # 병렬 평가 실행
            tasks = []
            evaluator_names = []
            
            # 기본 평가기들
            if products:  # API 데이터가 있을 때만
                tasks.extend([
                    self.rule_based.evaluate(keyword, products, screenshot_path),
                    self.keyword.evaluate(keyword, products, screenshot_path),
                    self.embedding.evaluate(keyword, products, screenshot_path)
                ])
                evaluator_names.extend(['rule_based', 'keyword', 'embedding'])
            
            if screenshot_path:  # 스크린샷이 있을 때만
                tasks.append(self.llm.evaluate(keyword, products, screenshot_path))
                evaluator_names.append('llm')
            
            # Individual Image LLM 평가기 (활성화된 경우에만)
            if self.enable_individual_image_llm and self.individual_image_llm and products:
                tasks.append(self.individual_image_llm.evaluate(keyword, products, screenshot_path))
                evaluator_names.append('individual_image_llm')
            
            if not tasks:
                return EvaluationResult(
                    method=self.name,
                    ndcg_10=0.0,
                    precision=0.0,
                    recall=0.0,
                    confidence=0.0,
                    details={"error": "실행 가능한 평가기가 없습니다"},
                    precision_issues=[]
                )
            
            # 병렬 실행
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 결과 처리
            individual_results = {}
            valid_results = []
            all_precision_issues = []
            
            for i, result in enumerate(results):
                evaluator_name = evaluator_names[i]
                
                if isinstance(result, Exception):
                    print(f"[{self.name}] {evaluator_name} 평가 실패: {result}")
                    individual_results[evaluator_name] = {
                        "error": str(result),
                        "included": False
                    }
                else:
                    individual_results[evaluator_name] = {
                        "ndcg_10": result.ndcg_10,
                        "precision": result.precision,
                        "recall": result.recall,
                        "confidence": result.confidence,
                        "weight": self._get_adjusted_weight(evaluator_name),
                        "included": True
                    }
                    valid_results.append((evaluator_name, result))
                    
                    # precision_issues 수집
                    if result.precision_issues:
                        all_precision_issues.extend(result.precision_issues)
            
            if not valid_results:
                return EvaluationResult(
                    method=self.name,
                    ndcg_10=0.0,
                    precision=0.0,
                    recall=0.0,
                    confidence=0.0,
                    details={"error": "모든 평가기가 실패했습니다", "individual_results": individual_results},
                    precision_issues=[]
                )
            
            # 가중 평균 계산
            final_ndcg, final_precision, final_recall, final_confidence = self._calculate_weighted_average(valid_results)
            
            # precision_issues 중복 제거 및 정리
            unique_precision_issues = self._deduplicate_precision_issues(all_precision_issues)
            
            print(f"[{self.name}] {keyword} 종합 평가 완료: NDCG={final_ndcg:.3f}, 신뢰도={final_confidence:.3f}")
            
            return EvaluationResult(
                method=self.name,
                ndcg_10=final_ndcg,
                precision=final_precision,
                recall=final_recall,
                confidence=final_confidence,
                details={
                    "individual_results": individual_results,
                    "weighting_strategy": "confidence_weighted",
                    "total_evaluators": len(evaluator_names),
                    "active_evaluators": len(valid_results),
                    "individual_image_llm_enabled": self.enable_individual_image_llm
                },
                precision_issues=unique_precision_issues
            )
            
        except Exception as e:
            print(f"[{self.name}] {keyword} 종합 평가 실패: {e}")
            return EvaluationResult(
                method=self.name,
                ndcg_10=0.0,
                precision=0.0,
                recall=0.0,
                confidence=0.0,
                details={"error": str(e)},
                precision_issues=[]
            )
    
    def _get_adjusted_weight(self, evaluator_name: str) -> float:
        """평가기별 조정된 가중치 반환"""
        if self.enable_individual_image_llm and self.individual_image_llm:
            # Individual Image LLM이 활성화된 경우 가중치 재조정
            adjusted_weights = {
                'rule_based': 0.15,
                'keyword': 0.15,
                'llm': 0.35,
                'embedding': 0.15,
                'individual_image_llm': 0.20
            }
            return adjusted_weights.get(evaluator_name, 0.0)
        else:
            # 기본 가중치
            return self.weights.get(evaluator_name, 0.0)
    
    def _calculate_weighted_average(self, valid_results: List) -> tuple:
        """가중 평균 계산"""
        total_weight = 0.0
        weighted_ndcg = 0.0
        weighted_precision = 0.0
        weighted_recall = 0.0
        weighted_confidence = 0.0
        
        for evaluator_name, result in valid_results:
            # 신뢰도 기반 동적 가중치 조정
            base_weight = self._get_adjusted_weight(evaluator_name)
            confidence_factor = result.confidence
            adjusted_weight = base_weight * confidence_factor
            
            total_weight += adjusted_weight
            weighted_ndcg += result.ndcg_10 * adjusted_weight
            weighted_precision += result.precision * adjusted_weight
            weighted_recall += result.recall * adjusted_weight
            weighted_confidence += result.confidence * adjusted_weight
        
        if total_weight == 0:
            return 0.0, 0.0, 0.0, 0.0
        
        return (
            weighted_ndcg / total_weight,
            weighted_precision / total_weight,
            weighted_recall / total_weight,
            weighted_confidence / total_weight
        )
    
    def _deduplicate_precision_issues(self, all_issues: List[Dict]) -> List[Dict]:
        """precision_issues 중복 제거 및 통합 - 각 평가기별 상세 이유 포함"""
        if not all_issues:
            return []
        
        # goods_no 기준으로 중복 제거 및 평가기별 이유 수집
        seen_goods = {}
        for issue in all_issues:
            goods_no = issue.get("goods_no", "")
            if goods_no and goods_no != "N/A":
                if goods_no in seen_goods:
                    # 기존 이슈에 평가기 정보 추가
                    existing_evaluator_reasons = seen_goods[goods_no].get("evaluator_reasons", [])
                    new_reason = issue.get("reason", "")
                    evaluator_name = self._extract_evaluator_name_from_reason(new_reason)
                    
                    # 중복되지 않는 평가기 이유만 추가
                    if not any(er["evaluator"] == evaluator_name for er in existing_evaluator_reasons):
                        existing_evaluator_reasons.append({
                            "evaluator": evaluator_name,
                            "reason": new_reason
                        })
                        seen_goods[goods_no]["evaluator_reasons"] = existing_evaluator_reasons
                else:
                    # 새로운 상품 추가
                    evaluator_name = self._extract_evaluator_name_from_reason(issue.get("reason", ""))
                    seen_goods[goods_no] = issue.copy()
                    seen_goods[goods_no]["evaluator_reasons"] = [{
                        "evaluator": evaluator_name,
                        "reason": issue.get("reason", "")
                    }]
        
        # 상위 6개만 반환 (UI 표시 제한)
        unique_issues = list(seen_goods.values())[:6]
        
        # 통합된 이유 생성
        for issue in unique_issues:
            evaluator_reasons = issue.get("evaluator_reasons", [])
            if len(evaluator_reasons) > 1:
                # 여러 평가기에서 문제 감지된 경우
                detailed_reasons = []
                for er in evaluator_reasons:
                    evaluator_display = self._get_evaluator_display_name(er["evaluator"])
                    detailed_reasons.append(f"• {evaluator_display}: {er['reason']}")
                
                issue["reason"] = f"다중 평가기에서 문제 감지 ({len(evaluator_reasons)}개)"
                issue["detailed_reasons"] = detailed_reasons
            else:
                # 단일 평가기에서만 문제 감지된 경우
                if evaluator_reasons:
                    evaluator_display = self._get_evaluator_display_name(evaluator_reasons[0]["evaluator"])
                    issue["reason"] = f"{evaluator_display}에서 문제 감지"
                    issue["detailed_reasons"] = [f"• {evaluator_display}: {evaluator_reasons[0]['reason']}"]
                else:
                    issue["detailed_reasons"] = [f"• 알 수 없음: {issue.get('reason', '')}"]
            
            # evaluator_reasons는 내부 처리용이므로 제거
            issue.pop("evaluator_reasons", None)
        
        return unique_issues
    
    def _extract_evaluator_name_from_reason(self, reason: str) -> str:
        """평가 이유에서 평가기 이름 추출"""
        if "Rule-Based" in reason or "규칙 기반" in reason:
            return "rule_based"
        elif "Keyword" in reason or "키워드" in reason:
            return "keyword"
        elif "LLM" in reason or "GPT" in reason:
            return "llm"
        elif "Embedding" in reason or "임베딩" in reason:
            return "embedding"
        elif "Individual-Image-LLM" in reason or "개별 이미지" in reason:
            return "individual_image_llm"
        elif "Composite" in reason or "종합" in reason:
            return "composite"
        else:
            return "unknown"
    
    def _get_evaluator_display_name(self, evaluator_name: str) -> str:
        """평가기 이름을 사용자 친화적인 한국어 이름으로 변환"""
        display_names = {
            "rule_based": "규칙 기반 평가기",
            "keyword": "키워드 기반 평가기", 
            "llm": "LLM 평가기",
            "embedding": "임베딩 기반 평가기",
            "individual_image_llm": "개별 이미지 LLM 평가기",
            "composite": "종합 평가기",
            "unknown": "알 수 없는 평가기"
        }
        return display_names.get(evaluator_name, evaluator_name) 