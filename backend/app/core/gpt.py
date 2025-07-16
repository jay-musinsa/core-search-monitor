import os
import base64
from typing import Dict
from openai import OpenAI
import json
import re
import sys

from app.core.prompt import get_prompt

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import config

class GPTMetricEvaluator:
    def __init__(self):
        api_key = config.get_openai_api_key()
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None
            print("[GPT] 경고: OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")

    def encode_image(self, image_path: str) -> str:
        """이미지를 base64로 인코딩"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"[GPT] 이미지 인코딩 실패: {e}")
            return None

    def evaluate(self, screenshot_path: str, keyword: str = None) -> Dict[str, float]:
        """GPT Vision API를 사용하여 검색 결과 스크린샷 분석 및 메트릭 계산"""
        print(f"[GPT] 평가 시작: 키워드 = {keyword}, 스크린샷 경로 = {screenshot_path}")
        # 실제 파일 경로로 변환
        if screenshot_path and screenshot_path.startswith("/screenshot/"):
            abs_path = os.path.join(os.path.dirname(__file__), "..", screenshot_path.lstrip("/"))
            abs_path = os.path.abspath(abs_path)
        else:
            abs_path = screenshot_path
        print(f"[GPT] 실제 파일 경로: {abs_path}")

        if not abs_path or not os.path.exists(abs_path):
            print(f"[GPT] 스크린샷 파일이 존재하지 않음: {abs_path}")
            return {
                "ndcg@10": 0.0, 
                "precision": 0.0, 
                "recall": 0.0,
                "ndcg_reason": "스크린샷 파일이 존재하지 않습니다.",
                "precision_reason": "스크린샷 파일이 존재하지 않습니다.",
                "recall_reason": "스크린샷 파일이 존재하지 않습니다."
            }

        if not self.client:
            print("[GPT] OpenAI API 키가 없어 시뮬레이션 결과 반환")
            return {
                "ndcg@10": 0.7, 
                "precision": 0.8, 
                "recall": 0.6,
                "ndcg_reason": "API 키가 없어 시뮬레이션 결과입니다.",
                "precision_reason": "API 키가 없어 시뮬레이션 결과입니다.",
                "recall_reason": "API 키가 없어 시뮬레이션 결과입니다."
            }

        try:
            # 이미지 base64 인코딩
            base64_image = self.encode_image(abs_path)
            print(f"[GPT] base64 인코딩 길이: {len(base64_image) if base64_image else 0}")
            if not base64_image:
                return {
                    "ndcg@10": 0.0, 
                    "precision": 0.0, 
                    "recall": 0.0,
                    "ndcg_reason": "이미지 인코딩에 실패했습니다.",
                    "precision_reason": "이미지 인코딩에 실패했습니다.",
                    "recall_reason": "이미지 인코딩에 실패했습니다."
                }

            print("[GPT] GPT Vision API 호출 시작")
            # GPT Vision API 호출
            response = self.client.chat.completions.create(
                model="gpt-4o",
                # model="gemini-2.5-pro",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": get_prompt(keyword)
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=800
            )

            print("[GPT] GPT Vision API 응답 수신")
            # 응답 파싱
            content = response.choices[0].message.content
            print(f"[GPT] 응답 내용: {content}")
            
            # GPT가 거부하는 경우 처리
            if "I'm sorry" in content or "I can't assist" in content or "cannot assist" in content:
                print("[GPT] GPT가 요청을 거부했습니다. 기본값 반환")
                return {
                    "ndcg@10": 0.5, 
                    "precision": 0.5, 
                    "recall": 0.5,
                    "ndcg_reason": "GPT가 콘텐츠 정책으로 인해 분석을 거부했습니다.",
                    "precision_reason": "GPT가 콘텐츠 정책으로 인해 분석을 거부했습니다.",
                    "recall_reason": "GPT가 콘텐츠 정책으로 인해 분석을 거부했습니다."
                }
            
            # JSON 파싱
            try:
                # 마크다운 코드 블록 제거
                cleaned_content = content.strip()
                if cleaned_content.startswith("```json"):
                    cleaned_content = cleaned_content[7:]  # ```json 제거
                if cleaned_content.startswith("```"):
                    cleaned_content = cleaned_content[3:]  # ``` 제거
                if cleaned_content.endswith("```"):
                    cleaned_content = cleaned_content[:-3]  # ``` 제거
                
                cleaned_content = cleaned_content.strip()
                
                # 정규식으로 JSON 객체 추출 (더 견고한 방법)
                json_match = re.search(r'\{.*\}', cleaned_content, re.DOTALL)
                if json_match:
                    cleaned_content = json_match.group(0)
                
                print(f"[GPT] 정리된 응답 내용: {cleaned_content}")
                
                metrics = json.loads(cleaned_content)
                print(f"[GPT] 파싱된 메트릭: {metrics}")
                return {
                    "ndcg@10": float(metrics.get("ndcg@10", 0.0)),
                    "precision": float(metrics.get("precision", 0.0)),
                    "recall": float(metrics.get("recall", 0.0)),
                    "ndcg_reason": metrics.get("ndcg_reason", "평가 이유를 확인할 수 없습니다."),
                    "precision_reason": metrics.get("precision_reason", "평가 이유를 확인할 수 없습니다."),
                    "recall_reason": metrics.get("recall_reason", "평가 이유를 확인할 수 없습니다.")
                }
            except json.JSONDecodeError as e:
                print(f"[GPT] JSON 파싱 실패: {e}")
                print(f"[GPT] 원본 응답: {content}")
                print(f"[GPT] 정리된 응답: {cleaned_content}")
                
                # 수동으로 값 추출 시도
                try:
                    ndcg_match = re.search(r'"ndcg@10":\s*([0-9.]+)', cleaned_content)
                    precision_match = re.search(r'"precision":\s*([0-9.]+)', cleaned_content)
                    recall_match = re.search(r'"recall":\s*([0-9.]+)', cleaned_content)
                    
                    if ndcg_match and precision_match and recall_match:
                        print("[GPT] 정규식으로 값 추출 성공")
                        return {
                            "ndcg@10": float(ndcg_match.group(1)),
                            "precision": float(precision_match.group(1)),
                            "recall": float(recall_match.group(1)),
                            "ndcg_reason": "정규식으로 추출된 값입니다.",
                            "precision_reason": "정규식으로 추출된 값입니다.",
                            "recall_reason": "정규식으로 추출된 값입니다."
                        }
                except Exception as regex_error:
                    print(f"[GPT] 정규식 추출도 실패: {regex_error}")
                
                return {
                    "ndcg@10": 0.7, 
                    "precision": 0.8, 
                    "recall": 0.6,
                    "ndcg_reason": "JSON 파싱 실패로 인한 기본값입니다.",
                    "precision_reason": "JSON 파싱 실패로 인한 기본값입니다.",
                    "recall_reason": "JSON 파싱 실패로 인한 기본값입니다."
                }

        except Exception as e:
            print(f"[GPT] API 호출 실패: {e}")
            return {
                "ndcg@10": 0.0, 
                "precision": 0.0, 
                "recall": 0.0,
                "ndcg_reason": f"API 호출 실패: {str(e)}",
                "precision_reason": f"API 호출 실패: {str(e)}",
                "recall_reason": f"API 호출 실패: {str(e)}"
            } 
