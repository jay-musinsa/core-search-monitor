import os
import base64
import json
import re
from typing import Dict, List, Any, Optional
from openai import OpenAI
from .base_evaluator import BaseEvaluator, EvaluationResult
from ..prompt import get_prompt, get_prompt_with_api_data
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from config import config

class LLMEvaluator(BaseEvaluator):
    """LLM 기반 평가기 - GPT, Gemini 등 다양한 모델 지원"""
    
    def __init__(self, model_name: str = "gpt-4o", provider: str = "openai"):
        super().__init__(f"LLM-{model_name}", default_confidence=0.8)
        self.model_name = model_name
        self.provider = provider
        self.client = None
        
        if provider == "openai":
            api_key = config.get_openai_api_key()
            if api_key:
                self.client = OpenAI(api_key=api_key)
            else:
                print(f"[{self.name}] 경고: OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        # TODO: Gemini, Claude 등 다른 provider 지원 추가
    
    async def evaluate(self, 
                      keyword: str, 
                      products: List[Dict[str, Any]], 
                      screenshot_path: Optional[str] = None,
                      **kwargs) -> EvaluationResult:
        """LLM 기반 평가 수행"""
        
        if not products and not screenshot_path:
            return EvaluationResult(
                ndcg_10=0.0,
                precision=0.0,
                recall=0.0,
                confidence=self.default_confidence,
                method=self.name,
                details={"reason": "상품 데이터와 스크린샷이 모두 없습니다."},
                precision_issues=[]
            )
        
        # API 데이터가 있으면 API 데이터 포함 평가, 없으면 스크린샷만 평가
        if products:
            return await self._evaluate_with_api_data(keyword, products, screenshot_path)
        else:
            return await self._evaluate_screenshot_only(keyword, screenshot_path)
    
    async def _evaluate_with_api_data(self, keyword: str, products: List[Dict[str, Any]], screenshot_path: Optional[str]) -> EvaluationResult:
        """API 데이터와 함께 평가"""
        print(f"[{self.name}] API 데이터와 함께 평가 시작: 키워드 = {keyword}")
        
        if not self.client:
            print(f"[{self.name}] API 키가 없어 시뮬레이션 결과 반환")
            return self._generate_simulation_result(keyword, products)
        
        # 스크린샷 처리
        base64_image = None
        if screenshot_path:
            base64_image = self._encode_image(screenshot_path)
        
        try:
            # LLM API 호출
            response = await self._call_llm_api(keyword, products, base64_image)
            
            if not response:
                return self._generate_fallback_result(keyword, products, "LLM API 호출 실패")
            
            # 응답 파싱
            parsed_result = self._parse_llm_response(response, products)
            
            return EvaluationResult(
                ndcg_10=parsed_result["ndcg@10"],
                precision=parsed_result["precision"],
                recall=parsed_result["recall"],
                confidence=self.default_confidence,
                method=self.name,
                details={
                    "model": self.model_name,
                    "provider": self.provider,
                    "total_products": len(products),
                    "has_screenshot": screenshot_path is not None,
                    "llm_reasoning": parsed_result.get("reasoning", "")
                },
                precision_issues=parsed_result.get("precision_issues", [])
            )
            
        except Exception as e:
            print(f"[{self.name}] 평가 실패: {e}")
            return self._generate_fallback_result(keyword, products, f"평가 실패: {str(e)}")
    
    async def _evaluate_screenshot_only(self, keyword: str, screenshot_path: str) -> EvaluationResult:
        """스크린샷만으로 평가 (29CM용)"""
        print(f"[{self.name}] 스크린샷만으로 평가 시작: 키워드 = {keyword}")
        
        if not self.client:
            print(f"[{self.name}] API 키가 없어 시뮬레이션 결과 반환")
            return self._generate_simulation_result(keyword, [])
        
        base64_image = self._encode_image(screenshot_path)
        if not base64_image:
            return self._generate_fallback_result(keyword, [], "이미지 인코딩 실패")
        
        try:
            # LLM API 호출 (스크린샷만)
            response = await self._call_llm_api(keyword, [], base64_image)
            
            if not response:
                return self._generate_fallback_result(keyword, [], "LLM API 호출 실패")
            
            # 응답 파싱
            parsed_result = self._parse_llm_response(response, [])
            
            return EvaluationResult(
                ndcg_10=parsed_result["ndcg@10"],
                precision=parsed_result["precision"],
                recall=parsed_result["recall"],
                confidence=self.default_confidence * 0.8,  # 스크린샷만 있을 때는 신뢰도 조금 낮춤
                method=self.name,
                details={
                    "model": self.model_name,
                    "provider": self.provider,
                    "evaluation_type": "screenshot_only",
                    "llm_reasoning": parsed_result.get("reasoning", "")
                },
                precision_issues=parsed_result.get("precision_issues", [])
            )
            
        except Exception as e:
            print(f"[{self.name}] 평가 실패: {e}")
            return self._generate_fallback_result(keyword, [], f"평가 실패: {str(e)}")
    
    async def _call_llm_api(self, keyword: str, products: List[Dict[str, Any]], base64_image: Optional[str]) -> Optional[str]:
        """LLM API 호출"""
        if self.provider == "openai":
            return await self._call_openai_api(keyword, products, base64_image)
        # TODO: 다른 provider 지원 추가
        return None
    
    async def _call_openai_api(self, keyword: str, products: List[Dict[str, Any]], base64_image: Optional[str]) -> Optional[str]:
        """OpenAI API 호출"""
        try:
            # 메시지 구성
            content = []
            
            # 텍스트 프롬프트
            if products:
                prompt_text = get_prompt_with_api_data(keyword, products)
            else:
                prompt_text = get_prompt(keyword)
            
            content.append({
                "type": "text",
                "text": prompt_text
            })
            
            # 이미지 추가 (있는 경우)
            if base64_image:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                })
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{
                    "role": "user",
                    "content": content
                }],
                max_tokens=1500 if products else 800
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"[{self.name}] OpenAI API 호출 실패: {e}")
            return None
    
    def _encode_image(self, image_path: str) -> Optional[str]:
        """이미지를 base64로 인코딩"""
        try:
            # 실제 파일 경로로 변환
            if image_path and image_path.startswith("/screenshot/"):
                abs_path = os.path.join(os.path.dirname(__file__), "..", "..", image_path.lstrip("/"))
                abs_path = os.path.abspath(abs_path)
            else:
                abs_path = image_path
            
            if not abs_path or not os.path.exists(abs_path):
                print(f"[{self.name}] 스크린샷 파일이 존재하지 않음: {abs_path}")
                return None
            
            with open(abs_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
                
        except Exception as e:
            print(f"[{self.name}] 이미지 인코딩 실패: {e}")
            return None
    
    def _parse_llm_response(self, response: str, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """LLM 응답 파싱"""
        try:
            # 마크다운 코드 블록 제거
            cleaned_content = response.strip()
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:]
            if cleaned_content.startswith("```"):
                cleaned_content = cleaned_content[3:]
            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3]
            
            cleaned_content = cleaned_content.strip()
            
            # 정규식으로 JSON 객체 추출
            json_match = re.search(r'\{.*\}', cleaned_content, re.DOTALL)
            if json_match:
                cleaned_content = json_match.group(0)
            
            metrics = json.loads(cleaned_content)
            
            # precision_issues에 이미지 URL 추가 (API 데이터가 있는 경우)
            if "precision_issues" in metrics and products:
                for issue in metrics["precision_issues"]:
                    goods_no = issue.get("goods_no")
                    # LLM 평가기 이름을 이유에 추가
                    original_reason = issue.get("reason", "관련성 낮음")
                    issue["reason"] = f"LLM 기반 평가: {original_reason}"
                    
                    if goods_no:
                        for product in products:
                            if str(product.get("goodsNo", "")) == str(goods_no):
                                issue["image_url"] = product.get("thumbnail", "N/A")
                                break
                        else:
                            issue["image_url"] = "N/A"
            elif "precision_issues" in metrics:
                # API 데이터가 없는 경우에도 평가기 이름 추가
                for issue in metrics["precision_issues"]:
                    original_reason = issue.get("reason", "관련성 낮음")
                    issue["reason"] = f"LLM 기반 평가: {original_reason}"
            
            return metrics
            
        except json.JSONDecodeError as e:
            print(f"[{self.name}] JSON 파싱 실패: {e}")
            # 정규식으로 값 추출 시도
            return self._extract_metrics_with_regex(response)
        except Exception as e:
            print(f"[{self.name}] 응답 파싱 실패: {e}")
            return {"ndcg@10": 0.5, "precision": 0.5, "recall": 0.5, "precision_issues": []}
    
    def _extract_metrics_with_regex(self, response: str) -> Dict[str, Any]:
        """정규식으로 메트릭 추출"""
        try:
            ndcg_match = re.search(r'"ndcg@10":\s*([0-9.]+)', response)
            precision_match = re.search(r'"precision":\s*([0-9.]+)', response)
            recall_match = re.search(r'"recall":\s*([0-9.]+)', response)
            
            if ndcg_match and precision_match and recall_match:
                return {
                    "ndcg@10": float(ndcg_match.group(1)),
                    "precision": float(precision_match.group(1)),
                    "recall": float(recall_match.group(1)),
                    "precision_issues": []
                }
        except Exception as e:
            print(f"[{self.name}] 정규식 추출 실패: {e}")
        
        return {"ndcg@10": 0.5, "precision": 0.5, "recall": 0.5, "precision_issues": []}
    
    def _generate_simulation_result(self, keyword: str, products: List[Dict[str, Any]]) -> EvaluationResult:
        """시뮬레이션 결과 생성"""
        precision_issues = []
        
        if products:
            # 모든 상품을 이슈로 표시 (시뮬레이션)
            for product in products:
                precision_issues.append({
                    "goods_no": product.get("goodsNo", 1234567),
                    "goods_name": product.get("goodsName", "시뮬레이션 상품"),
                    "image_url": product.get("thumbnail", "N/A"),
                    "reason": f"{self.name} API 키가 없어 시뮬레이션 결과입니다."
                })
        
        return EvaluationResult(
            ndcg_10=0.7,
            precision=0.8,
            recall=0.6,
            confidence=0.3,  # 시뮬레이션은 신뢰도 낮음
            method=self.name,
            details={
                "simulation": True,
                "reason": "API 키가 없어 시뮬레이션 결과입니다.",
                "model": self.model_name,
                "provider": self.provider
            },
            precision_issues=precision_issues
        )
    
    def _generate_fallback_result(self, keyword: str, products: List[Dict[str, Any]], reason: str) -> EvaluationResult:
        """폴백 결과 생성"""
        return EvaluationResult(
            ndcg_10=0.0,
            precision=0.0,
            recall=0.0,
            confidence=0.0,
            method=self.name,
            details={
                "error": True,
                "reason": reason,
                "model": self.model_name,
                "provider": self.provider
            },
            precision_issues=[]
        ) 