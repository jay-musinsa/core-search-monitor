from fastapi import APIRouter, WebSocket, Depends, BackgroundTasks, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime
import asyncio
import os
from typing import List
from concurrent.futures import ThreadPoolExecutor
from app.core.metrics import metrics_manager

router = APIRouter()

# WebSocket 연결 관리
websocket_connections: List[WebSocket] = []

# 키워드 입력 모델
class KeywordRequest(BaseModel):
    keyword: str

# 모든 WebSocket 클라이언트에게 브로드캐스트
async def broadcast_update():
    print(f"[브로드캐스트] 연결된 WebSocket 수: {len(websocket_connections)}")
    if not websocket_connections:
        print("[브로드캐스트] 연결된 WebSocket이 없습니다.")
        return
    
    message = {
        "metrics": {},  # 메트릭 저장하지 않으므로 빈 객체
        "timestamp": datetime.now().isoformat()
    }
    
    # 연결이 끊긴 WebSocket 제거
    disconnected = []
    for i, ws in enumerate(websocket_connections):
        try:
            await ws.send_json(message)
            print(f"[브로드캐스트] WebSocket {i}에 메시지 전송 완료")
        except Exception as e:
            print(f"[브로드캐스트] WebSocket {i} 전송 실패: {e}")
            disconnected.append(ws)
    
    for ws in disconnected:
        websocket_connections.remove(ws)
    
    print(f"[브로드캐스트] 브로드캐스트 완료. 활성 연결: {len(websocket_connections)}")

# 상태 브로드캐스트 (프로그레스 업데이트용)
async def broadcast_status(keyword: str, status: str, step: int, total_steps: int):
    print(f"[상태 브로드캐스트] {keyword}: {status} ({step}/{total_steps})")
    if not websocket_connections:
        print("[상태 브로드캐스트] 연결된 WebSocket이 없습니다.")
        return
    
    message = {
        "type": "status",
        "keyword": keyword,
        "status": status,
        "step": step,
        "total_steps": total_steps,
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"[상태 브로드캐스트] 전송할 메시지: {message}")
    
    # 연결이 끊긴 WebSocket 제거
    disconnected = []
    for i, ws in enumerate(websocket_connections):
        try:
            await ws.send_json(message)
            print(f"[상태 브로드캐스트] WebSocket {i}에 상태 메시지 전송 완료")
            # 각 WebSocket 전송 후 이벤트 루프 양보
            await asyncio.sleep(0)
        except Exception as e:
            print(f"[상태 브로드캐스트] WebSocket {i} 전송 실패: {e}")
            disconnected.append(ws)
    
    for ws in disconnected:
        websocket_connections.remove(ws)
    
    # 모든 전송 완료 후 이벤트 루프 양보
    await asyncio.sleep(0)
    print(f"[상태 브로드캐스트] 상태 브로드캐스트 완료: {keyword}")

# 개별 메트릭 업데이트 브로드캐스트
async def broadcast_individual_metric_update(keyword: str, metrics: dict):
    print(f"[개별 메트릭 업데이트] {keyword}")
    print(f"[개별 메트릭 업데이트] 전송할 데이터: {metrics}")
    if not websocket_connections:
        print("[개별 메트릭 업데이트] 연결된 WebSocket이 없습니다.")
        return
    
    message = {
        "type": "metric_update",
        "keyword": keyword,
        "metrics": metrics,
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"[개별 메트릭 업데이트] 전송할 메시지: {message}")
    
    # 연결이 끊긴 WebSocket 제거
    disconnected = []
    for i, ws in enumerate(websocket_connections):
        try:
            await ws.send_json(message)
            print(f"[개별 메트릭 업데이트] WebSocket {i}에 메트릭 메시지 전송 완료")
            await asyncio.sleep(0)
        except Exception as e:
            print(f"[개별 메트릭 업데이트] WebSocket {i} 전송 실패: {e}")
            disconnected.append(ws)
    
    for ws in disconnected:
        websocket_connections.remove(ws)
    
    await asyncio.sleep(0)
    print(f"[개별 메트릭 업데이트] 메트릭 업데이트 완료: {keyword}")

# 키워드 입력 시 호출될 파이프라인
async def on_keyword_message(keyword: str):
    print(f"[파이프라인] 키워드 처리 시작: {keyword}")

    try:
        # 1단계: API 데이터 수집 및 스크린샷 캡처 진행중
        await broadcast_status(keyword, "API 데이터 수집 및 스크린샷 캡처 진행중", 1, 3)
        await asyncio.sleep(0.5)

        # 새로운 메트릭 서비스로 키워드 처리
        result = await metrics_manager.process_keyword(keyword)
        
        if "error" in result:
            print(f"[파이프라인] 키워드 처리 실패: {result['error']}")
            await broadcast_status(keyword, "처리 실패", 3, 3)
            return

        # 2단계: 데이터 처리 완료
        await broadcast_status(keyword, "데이터 처리 완료", 2, 3)
        await asyncio.sleep(0.5)

        # 3단계: 완료
        await broadcast_status(keyword, "완료", 3, 3)
        await asyncio.sleep(0.5)

        # 개별 메트릭 업데이트 브로드캐스트 - process_keyword 결과 직접 사용
        await broadcast_individual_metric_update(keyword, result)

        print(f"[파이프라인] 키워드 처리 완료: {keyword}")
        print(f"[파이프라인] 결과: {result}")

    except Exception as e:
        print(f"[파이프라인] 키워드 처리 중 오류: {e}")
        await broadcast_status(keyword, "오류 발생", 3, 3)

    # broadcast_update 제거 - 메트릭 데이터가 지워지지 않도록

@router.get("/api/metrics")
async def get_metrics():
    """모든 메트릭 조회"""
    return {
        "metrics": {},  # 메트릭 저장하지 않으므로 빈 객체
        "last_updated": datetime.now().isoformat()
    }

@router.get("/api/metrics/summary")
async def get_metrics_summary():
    """메트릭 요약 정보 조회"""
    return metrics_manager.get_metrics_summary()

@router.delete("/api/metrics")
async def clear_metrics(keyword: str = None):
    """메트릭 초기화"""
    metrics_manager.clear_metrics(keyword)
    await broadcast_update()
    return {"message": "메트릭이 초기화되었습니다."}

@router.post("/api/keyword")
async def post_keyword(req: KeywordRequest, background_tasks: BackgroundTasks):
    """키워드 입력 처리"""
    print(f"[API] 키워드 입력 받음: {req.keyword}")
    
    # 백그라운드에서 키워드 처리
    background_tasks.add_task(on_keyword_message, req.keyword)
    
    return {"message": f"키워드 '{req.keyword}' 처리가 시작되었습니다."}

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 연결 처리"""
    await websocket.accept()
    websocket_connections.append(websocket)
    print(f"[WebSocket] 새 연결 추가. 총 연결 수: {len(websocket_connections)}")
    
    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_text()
            print(f"[WebSocket] 메시지 수신: {data}")
            
            # 키워드 메시지 처리
            if data.startswith("keyword:"):
                keyword = data.split(":", 1)[1].strip()
                print(f"[WebSocket] 키워드 처리 요청: {keyword}")
                await on_keyword_message(keyword)
            
    except Exception as e:
        print(f"[WebSocket] 연결 오류: {e}")
    finally:
        # 연결 제거
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)
        print(f"[WebSocket] 연결 제거. 남은 연결 수: {len(websocket_connections)}")

@router.get("/screenshot/{platform}/{filename}")
async def get_screenshot(platform: str, filename: str):
    """스크린샷 파일 제공"""
    screenshot_path = os.path.join(os.path.dirname(__file__), f"../screenshot/{platform}/{filename}")
    
    if os.path.exists(screenshot_path):
        return FileResponse(screenshot_path, media_type="image/png")
    else:
        return JSONResponse(
            status_code=404,
            content={"error": "스크린샷을 찾을 수 없습니다."}
        ) 
