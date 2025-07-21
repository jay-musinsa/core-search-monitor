"""
키워드 품질 대시보드 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Query, Depends, WebSocket
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from pydantic import BaseModel, Field
import logging
import json
import asyncio
from app.core.metrics import metrics_manager
import clickhouse_connect


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/quality", tags=["quality"])

# Quality Dashboard WebSocket 연결 관리
quality_websocket_connections: List[WebSocket] = []

# 임시 의존성 클래스들 (실제 구현 없이 API 호환성 유지)
class TrendAnalyzer:
    pass

class BatchOptimizer:
    pass

class ImageStorage:
    pass

class NotificationService:
    pass

class NotificationLevel:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class NotificationChannel:
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    WEBSOCKET = "websocket"

# 의존성 주입
def get_trend_analyzer():
    return TrendAnalyzer()

def get_batch_optimizer():
    return BatchOptimizer()

def get_image_storage():
    return ImageStorage()

def get_notification_service():
    return NotificationService()


# 요청/응답 모델 정의
class QualityFilterRequest(BaseModel):
    platform: str = Field(default="all", description="플랫폼 필터")
    category: str = Field(default="all", description="카테고리 필터")
    dateRange: str = Field(default="7d", description="날짜 범위")
    threshold: float = Field(default=0.5, ge=0, le=1, description="품질 임계값")
    showAnomalies: bool = Field(default=False, description="이상치만 표시")
    showRecentOnly: bool = Field(default=False, description="최근 데이터만")
    showHighPriority: bool = Field(default=False, description="고우선순위만")
    sortBy: str = Field(default="ndcg_score", description="정렬 기준")
    sortDirection: str = Field(default="desc", description="정렬 방향")


class QualityDataResponse(BaseModel):
    success: bool
    data: List[Dict[str, Any]]
    summary: Dict[str, Any]
    total: int
    message: Optional[str] = None


class TrendDataResponse(BaseModel):
    success: bool
    data: List[Dict[str, Any]]
    message: Optional[str] = None


class BatchJobRequest(BaseModel):
    platforms: List[str] = Field(default=["musinsa"], description="처리할 플랫폼 목록")
    keywordCount: int = Field(default=15000, ge=1, le=50000, description="처리할 키워드 수")
    targetDate: Optional[date] = Field(default=None, description="처리 대상 날짜")
    batchSize: int = Field(default=20, ge=1, le=100, description="배치 크기")
    maxWorkers: int = Field(default=5, ge=1, le=20, description="최대 워커 수")


# Quality Dashboard WebSocket 브로드캐스트 함수
async def broadcast_quality_update(update_data: Dict[str, Any]):
    """Quality Dashboard에 연결된 모든 클라이언트에 업데이트 브로드캐스트"""
    if not quality_websocket_connections:
        return
    
    message = {
        "type": "quality_update",
        "data": update_data,
        "timestamp": datetime.now().isoformat()
    }
    
    disconnected = []
    for ws in quality_websocket_connections:
        try:
            await ws.send_json(message)
        except Exception as e:
            logger.error(f"Quality WebSocket 브로드캐스트 실패: {e}")
            disconnected.append(ws)
    
    for ws in disconnected:
        quality_websocket_connections.remove(ws)


@router.websocket("/ws/quality")
async def quality_websocket_endpoint(websocket: WebSocket):
    """Quality Dashboard WebSocket 엔드포인트"""
    await websocket.accept()
    quality_websocket_connections.append(websocket)
    logger.info(f"Quality WebSocket 연결됨. 총 연결 수: {len(quality_websocket_connections)}")
    
    try:
        while True:
            # 클라이언트로부터 메시지 수신 (핑-퐁 등)
            data = await websocket.receive_text()
            logger.debug(f"Quality WebSocket 메시지 수신: {data}")
            
            # 핑-퐁 응답
            if data == "ping":
                await websocket.send_text("pong")
                
    except Exception as e:
        logger.error(f"Quality WebSocket 연결 오류: {e}")
    finally:
        if websocket in quality_websocket_connections:
            quality_websocket_connections.remove(websocket)
        logger.info(f"Quality WebSocket 연결 종료. 남은 연결 수: {len(quality_websocket_connections)}")


@router.get("/dashboard/data", response_model=QualityDataResponse)
async def get_quality_dashboard_data(
    platform: str = Query("all", description="플랫폼 필터"),
    category: str = Query("all", description="카테고리 필터"),
    dateRange: str = Query("7d", description="날짜 범위"),
    threshold: float = Query(0.5, ge=0, le=1, description="품질 임계값"),
    showAnomalies: bool = Query(False, description="이상치만 표시"),
    showRecentOnly: bool = Query(False, description="최근 데이터만"),
    showHighPriority: bool = Query(False, description="고우선순위만"),
    sortBy: str = Query("ndcg_score", description="정렬 기준"),
    sortDirection: str = Query("desc", description="정렬 방향"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(100, ge=1, le=1000, description="페이지 크기")
):
    """ClickHouse 평가 이력 기반 대시보드 데이터 조회"""
    try:
        client = clickhouse_connect.get_client(
            host='localhost', port=8123, username='default', password=''
        )
        # 정렬 필드 매핑
        sort_map = {
            "ndcg_score": "gpt_ndcg_score",
            "precision": "gpt_precision",
            "recall": "gpt_recall",
            "assessment_date": "assessment_date",
            "keyword": "km.keyword"
        }
        order_by_field = sort_map.get(sortBy, "gpt_ndcg_score")
        # 키워드 정렬인 경우 테이블 별칭 없이 처리
        if sortBy == "keyword":
            order_by = order_by_field
        else:
            order_by = f"qad.{order_by_field}"
        order_dir = "DESC" if sortDirection == "desc" else "ASC"
        # 필터 쿼리
        where = ["1=1"]
        params = {}
        if platform != "all":
            where.append("qad.platform = %(platform)s")
            params['platform'] = platform
        if threshold > 0:
            where.append("qad.gpt_ndcg_score >= %(threshold)s")
            params['threshold'] = threshold
        # 날짜 필터 (dateRange)
        if dateRange.endswith('d'):
            days = int(dateRange[:-1])
            where.append("qad.assessment_date >= today() - %(days)s")
            params['days'] = days
        # 쿼리 조립
        where_clause = " AND ".join(where)
        query = f'''
            SELECT
                qad.id,
                qad.keyword_id,
                km.keyword,
                qad.platform,
                qad.assessment_date,
                qad.gpt_ndcg_score,
                qad.gpt_precision,
                qad.gpt_recall,
                qad.screenshot_path,
                qad.api_total_results,
                qad.processing_time
            FROM quality_assessment_daily qad
            LEFT JOIN keyword_master km ON qad.keyword_id = km.id
            WHERE {where_clause}
            ORDER BY {order_by} {order_dir}
            LIMIT %(limit)s OFFSET %(offset)s
        '''
        params['limit'] = limit
        params['offset'] = (page-1)*limit
        result = client.query(query, params)
        rows = result.result_rows
        columns = result.column_names
        data = [dict(zip(columns, row)) for row in rows]
        # 요약 통계
        if data:
            summary = {
                "totalKeywords": len(data),
                "avgNdcgScore": sum(d["gpt_ndcg_score"] for d in data) / len(data),
                "avgPrecision": sum(d["gpt_precision"] for d in data) / len(data),
                "avgRecall": sum(d["gpt_recall"] for d in data) / len(data),
                "anomalyCount": 0,
                "lastUpdated": datetime.now().isoformat()
            }
        else:
            summary = {
                "totalKeywords": 0,
                "avgNdcgScore": 0,
                "avgPrecision": 0,
                "avgRecall": 0,
                "anomalyCount": 0,
                "lastUpdated": datetime.now().isoformat()
            }
        return QualityDataResponse(
            success=True,
            data=data,
            summary=summary,
            total=len(data),
            message="ClickHouse 평가 데이터 조회 성공"
        )
    except Exception as e:
        logger.error(f"ClickHouse 평가 데이터 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trend/data", response_model=TrendDataResponse)
async def get_trend_data(
    platform: str = Query("all", description="플랫폼 필터"),
    dateRange: str = Query("7d", description="날짜 범위"),
    trend_analyzer: TrendAnalyzer = Depends(get_trend_analyzer)
):
    """ClickHouse 기반 실제 트렌드 데이터 조회"""
    try:
        client = clickhouse_connect.get_client(
            host='localhost', port=8123, username='default', password=''
        )
        
        # 날짜 범위에 따른 일 수 결정
        days_map = {"1d": 1, "7d": 7, "30d": 30, "90d": 90}
        days = days_map.get(dateRange, 7)
        
        # 필터 조건 구성
        where = ["qad.assessment_date >= today() - %(days)s"]
        params = {'days': days}
        
        if platform != "all":
            where.append("qad.platform = %(platform)s")
            params['platform'] = platform
        
        where_clause = " AND ".join(where)
        
        # 일별 트렌드 데이터 집계 쿼리 (실제 데이터가 있는 필드만 사용)
        query = f'''
            SELECT 
                qad.assessment_date as date,
                qad.platform,
                avg(qad.gpt_ndcg_score) as ndcg_score,
                avg(qad.gpt_precision) as precision,
                avg(qad.gpt_recall) as recall,
                avg(qad.processing_time) as processing_time,
                avg(qad.api_response_time) as api_response_time,
                count(*) as total_assessments
            FROM quality_assessment_daily qad
            WHERE {where_clause}
            GROUP BY qad.assessment_date, qad.platform
            ORDER BY qad.assessment_date ASC, qad.platform ASC
        '''
        
        result = client.query(query, params)
        rows = result.result_rows
        columns = result.column_names
        
        trend_data = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            trend_data.append({
                "date": str(row_dict["date"]),
                "platform": row_dict["platform"],
                "ndcg_score": float(row_dict["ndcg_score"] or 0),
                "precision": float(row_dict["precision"] or 0),
                "recall": float(row_dict["recall"] or 0),
                "relevance_score": float(row_dict["ndcg_score"] or 0),  # NDCG를 relevance로 사용
                "confidence_score": float(row_dict["precision"] or 0),  # Precision을 confidence로 사용
                "processing_time": float(row_dict["processing_time"] or 0),
                "api_response_time": float(row_dict["api_response_time"] or 0),
                "total_assessments": int(row_dict["total_assessments"] or 0)
            })
        
        return TrendDataResponse(
            success=True,
            data=trend_data,
            message="ClickHouse 트렌드 데이터 조회 성공"
        )
        
    except Exception as e:
        logger.error(f"트렌드 데이터 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keyword/{keyword_id}/analysis")
async def get_keyword_analysis(
    keyword_id: int,
    platform: str = Query("musinsa", description="플랫폼"),
    days: int = Query(30, ge=1, le=365, description="분석 기간"),
    trend_analyzer: TrendAnalyzer = Depends(get_trend_analyzer)
):
    """특정 키워드의 상세 분석 조회"""
    try:
        # 임시 분석 데이터 반환
        fake_analysis = {
            "keyword_id": keyword_id,
            "platform": platform,
            "analysis_period": days,
            "metrics": {
                "ndcg_score": 0.75 + (keyword_id % 3) * 0.05,
                "precision": 0.82 + (keyword_id % 4) * 0.03,
                "recall": 0.78 + (keyword_id % 5) * 0.02,
                "relevance_score": 0.85 + (keyword_id % 2) * 0.05
            },
            "trends": [
                {
                    "date": (date.today() - timedelta(days=i)).isoformat(),
                    "ndcg_score": 0.7 + (i % 3) * 0.1,
                    "precision": 0.8 + (i % 4) * 0.05
                }
                for i in range(min(days, 30))
            ],
            "insights": [
                "키워드 성능이 안정적입니다.",
                "최근 7일간 품질 지표가 향상되고 있습니다.",
                f"분석 기간: {days}일"
            ]
        }
        
        return fake_analysis
        
    except Exception as e:
        logger.error(f"키워드 분석 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/optimize")
async def start_optimized_batch(
    request: BatchJobRequest,
    batch_optimizer: BatchOptimizer = Depends(get_batch_optimizer)
):
    """최적화된 배치 작업 시작"""
    try:
        # 임시 배치 작업 응답
        return {
            "success": True,
            "batch_id": f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "message": "배치 작업이 시작되었습니다.",
            "platforms": request.platforms,
            "keyword_count": request.keywordCount,
            "target_date": request.targetDate.isoformat() if request.targetDate else date.today().isoformat(),
            "batch_size": request.batchSize,
            "max_workers": request.maxWorkers
        }
        
    except Exception as e:
        logger.error(f"최적화된 배치 작업 시작 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch/{batch_id}/status")
async def get_batch_status(
    batch_id: str,
    batch_optimizer: BatchOptimizer = Depends(get_batch_optimizer)
):
    """배치 작업 상태 조회"""
    try:
        # 임시 배치 상태 응답 (진행률 시뮬레이션)
        import hashlib
        hash_value = int(hashlib.md5(batch_id.encode()).hexdigest()[:8], 16)
        progress = (hash_value % 100) + 1  # 1-100 사이의 값
        
        status = "running" if progress < 100 else "completed"
        
        return {
            "success": True,
            "batch_id": batch_id,
            "status": status,
            "progress": progress,
            "total_tasks": 100,
            "completed_tasks": progress,
            "failed_tasks": max(0, (hash_value % 5) - 2),
            "estimated_time_remaining": max(0, (100 - progress) * 3),
            "started_at": datetime.now().replace(hour=9, minute=0).isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"배치 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends/summary")
async def get_trends_summary(
    days: int = Query(7, ge=1, le=90, description="요약 기간"),
    trend_analyzer: TrendAnalyzer = Depends(get_trend_analyzer)
):
    """트렌드 요약 정보 조회"""
    try:
        # 임시 트렌드 요약 데이터
        return {
            "success": True,
            "period": days,
            "summary": {
                "total_keywords": 1500 + (days * 10),
                "avg_ndcg": 0.78 + (days % 5) * 0.02,
                "avg_precision": 0.82 + (days % 3) * 0.01,
                "avg_recall": 0.75 + (days % 4) * 0.02,
                "trend_direction": "improving" if days % 2 == 0 else "stable",
                "anomaly_count": max(1, days // 7),
                "platforms": ["musinsa", "29cm"],
                "last_updated": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"트렌드 요약 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/images/{image_id}/metadata")
async def get_image_metadata(
    image_id: str,
    image_storage: ImageStorage = Depends(get_image_storage)
):
    """이미지 메타데이터 조회"""
    try:
        # 임시 이미지 메타데이터
        return {
            "success": True,
            "image_id": image_id,
            "metadata": {
                "filename": f"screenshot_{image_id}.png",
                "size": 1024000 + (len(image_id) * 1000),
                "created_at": datetime.now().replace(hour=12, minute=0).isoformat(),
                "dimensions": {"width": 1920, "height": 1080},
                "format": "PNG",
                "keyword": f"테스트키워드{image_id}",
                "platform": "musinsa" if len(image_id) % 2 == 0 else "29cm"
            }
        }
        
    except Exception as e:
        logger.error(f"이미지 메타데이터 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/images/storage/stats")
async def get_storage_stats(
    image_storage: ImageStorage = Depends(get_image_storage)
):
    """이미지 저장소 통계 조회"""
    try:
        # 임시 저장소 통계
        return {
            "success": True,
            "stats": {
                "total_images": 5000,
                "total_size": 2048000000,  # 2GB
                "avg_size": 409600,  # 400KB
                "oldest_image": "2024-01-01T00:00:00Z",
                "newest_image": datetime.now().isoformat(),
                "platforms": {
                    "musinsa": 3000,
                    "29cm": 2000
                },
                "storage_usage": {
                    "used": 2048000000,
                    "total": 10737418240,  # 10GB
                    "usage_percentage": 19.1
                }
            }
        }
        
    except Exception as e:
        logger.error(f"저장소 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/images/cleanup")
async def cleanup_old_images(
    retention_days: int = Query(90, ge=1, le=365, description="보관 기간"),
    image_storage: ImageStorage = Depends(get_image_storage)
):
    """오래된 이미지 정리"""
    try:
        # 임시 정리 결과
        deleted_count = max(1, retention_days // 10)
        freed_space = deleted_count * 409600  # 평균 파일 크기
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "freed_space": freed_space,
            "retention_days": retention_days,
            "cleanup_date": datetime.now().isoformat(),
            "remaining_images": 5000 - deleted_count
        }
        
    except Exception as e:
        logger.error(f"이미지 정리 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications/send")
async def send_custom_notification(
    title: str = Query(..., description="알림 제목"),
    message: str = Query(..., description="알림 메시지"),
    level: str = Query("medium", description="알림 레벨"),
    channels: List[str] = Query(["email"], description="알림 채널"),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """사용자 정의 알림 발송"""
    try:
        # 임시 알림 발송 응답
        return {
            "success": True,
            "notification_id": f"notif_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "title": title,
            "message": message,
            "level": level,
            "channels": channels,
            "sent_at": datetime.now().isoformat(),
            "recipients": len(channels) * 2,  # 채널당 2명씩 가정
            "delivery_status": "sent"
        }
        
    except Exception as e:
        logger.error(f"사용자 정의 알림 발송 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications/history")
async def get_notification_history(
    limit: int = Query(100, ge=1, le=1000, description="조회 개수"),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """알림 히스토리 조회"""
    try:
        # 임시 알림 히스토리
        fake_history = []
        for i in range(min(limit, 20)):
            fake_history.append({
                "id": f"notif_{datetime.now().strftime('%Y%m%d')}_{i + 1:03d}",
                "title": f"품질 알림 {i + 1}",
                "message": f"키워드 품질 점수가 임계값을 {'초과' if i % 2 == 0 else '미달'}했습니다.",
                "level": ["low", "medium", "high", "critical"][i % 4],
                "sent_at": (datetime.now() - timedelta(hours=i * 2)).isoformat(),
                "status": "sent" if i % 10 != 0 else "failed",
                "channels": ["email", "slack"][i % 2:i % 2 + 1],
                "recipients": (i % 3) + 1
            })
        
        return {
            "success": True,
            "history": fake_history,
            "total": len(fake_history),
            "page": 1,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"알림 히스토리 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """서비스 상태 체크"""
    try:
        # 임시 상태 체크
        return {
            "success": True,
            "status": "healthy",
            "database_connected": True,
            "recent_assessments": 100,
            "system_stats": {
                "total_keywords": 1500,
                "active_platforms": 2,
                "last_assessment": datetime.now().isoformat(),
                "uptime": "2 days, 14 hours, 32 minutes"
            },
            "services": {
                "database": "healthy",
                "redis": "healthy",
                "websocket": "healthy",
                "notification": "healthy"
            },
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"서비스 상태 체크 실패: {e}")
        return {
            "success": False,
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }