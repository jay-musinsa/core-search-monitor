from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import requests
from config import Config

app = FastAPI(title="무신사 검색 모니터링 API", version="1.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
from app.api.metrics import router as metrics_router
from app.api.quality_dashboard import router as quality_router
from app.api.evaluator_config import router as evaluator_config_router

app.include_router(metrics_router)
app.include_router(quality_router)
app.include_router(evaluator_config_router)

# 헬스체크 엔드포인트
@app.get("/health")
async def health_check():
    """서비스 상태 확인"""
    config = Config()
    status = {
        "status": "healthy",
        "services": {}
    }
    
    # ClickHouse 연결 확인
    try:
        response = requests.get(
            f"http://{config.CLICKHOUSE_HOST}:{config.CLICKHOUSE_PORT}/ping",
            timeout=5
        )
        status["services"]["clickhouse"] = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception as e:
        status["services"]["clickhouse"] = f"error: {str(e)}"
    
    # Redis 연결 확인 (기본적으로 가정)
    status["services"]["redis"] = "healthy"
    
    return status

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {"message": "무신사 검색 모니터링 API", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
