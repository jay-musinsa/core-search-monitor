import os
from typing import Optional

class Config:
    """애플리케이션 설정"""
    
    # OpenAI API 설정
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # 환경 설정
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # 서버 설정
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # CORS 설정
    CORS_ORIGINS: list = ["http://localhost:3000"]
    
    @classmethod
    def get_openai_api_key(cls) -> Optional[str]:
        """OpenAI API 키 반환"""
        return cls.OPENAI_API_KEY
    
    @classmethod
    def is_production(cls) -> bool:
        """운영 환경 여부 확인"""
        return cls.ENVIRONMENT == "production"

# 전역 설정 인스턴스
config = Config() 