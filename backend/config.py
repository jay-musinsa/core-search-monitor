import os
from typing import Optional
from pathlib import Path

# .env 파일 로드
try:
    from dotenv import load_dotenv
    
    # 현재 파일 기준으로 .env 파일 경로 찾기
    current_dir = Path(__file__).parent
    env_file = current_dir / '.env'
    
    # .env 파일이 존재하면 로드
    if env_file.exists():
        load_dotenv(env_file)
        print(f"[Config] .env 파일 로드 완료: {env_file}")
    else:
        print(f"[Config] .env 파일이 없습니다: {env_file}")
        
except ImportError:
    print("[Config] python-dotenv가 설치되지 않았습니다. 'pip install python-dotenv' 실행하세요.")

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
    
    # ClickHouse 설정
    CLICKHOUSE_HOST: str = os.getenv("CLICKHOUSE_HOST", "localhost")
    CLICKHOUSE_PORT: int = int(os.getenv("CLICKHOUSE_PORT", "8123"))
    CLICKHOUSE_USER: str = os.getenv("CLICKHOUSE_USER", "default")
    CLICKHOUSE_PASSWORD: str = os.getenv("CLICKHOUSE_PASSWORD", "")
    CLICKHOUSE_DATABASE: str = os.getenv("CLICKHOUSE_DATABASE", "default")
    
    # Redis 설정
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    # Kafka 설정
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    
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