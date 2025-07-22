"""
평가기 설정 API
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import os
import json

router = APIRouter()

CONFIG_FILE = "evaluator_config.json"

@router.get("/api/evaluator-config")
async def get_evaluator_config():
    """평가기 설정 조회"""
    try:
        # 기본 설정
        default_config = {
            "rule_based": {"enabled": True, "weight": 0.2},
            "keyword": {"enabled": True, "weight": 0.2},
            "llm": {"enabled": True, "weight": 0.4},
            "embedding": {"enabled": True, "weight": 0.2},
            "individual_image_llm": {
                "enabled": False, 
                "weight": 0.3, 
                "confidence_threshold": 0.5,
                "max_products": 50  # 평가할 최대 상품 수
            }
        }
        
        # 파일에서 설정 로드
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved_config = json.load(f)
                # 기본 설정과 병합
                for key, value in saved_config.items():
                    if key in default_config:
                        default_config[key].update(value)
        
        return {
            "success": True,
            "configs": default_config
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "configs": {}
        }

@router.post("/api/evaluator-config")
async def save_evaluator_config(configs: Dict[str, Any]):
    """평가기 설정 저장"""
    try:
        # Individual Image LLM 설정이 변경된 경우 환경 변수 업데이트
        if "individual_image_llm" in configs:
            individual_llm_config = configs["individual_image_llm"]
            if individual_llm_config.get("enabled", False):
                # 환경 변수 파일 업데이트 (실제 서버 재시작 필요)
                print("[평가기 설정] Individual Image LLM 활성화 요청됨")
                print("[평가기 설정] 주의: 서버 재시작 후 적용됩니다")
        
        # 설정을 파일에 저장
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(configs, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "message": "설정이 저장되었습니다"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        } 