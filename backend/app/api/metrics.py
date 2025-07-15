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
from app.core.crawler import MusinsaCrawler
from app.core.gpt import GPTMetricEvaluator

router = APIRouter()

# 크롤러, GPT 인스턴스 생성
crawler = MusinsaCrawler()
gpt_evaluator = GPTMetricEvaluator()

# 스레드 풀 생성
executor = ThreadPoolExecutor(max_workers=2)

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
        "metrics": metrics_manager.get_metrics(),
        "timestamp": metrics_manager.get_last_updated()
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

# 키워드 입력 시 호출될 파이프라인
async def on_keyword_message(keyword: str):
    print(f"[파이프라인] 키워드 처리 시작: {keyword}")
    
    # 1단계: 무신사 검색 진행중
    await broadcast_status(keyword, "무신사 검색 진행중", 1, 3)
    await asyncio.sleep(0.5)  # 상태 전송 대기
    
    # 스크린샷 작업을 스레드 풀에서 실행
    loop = asyncio.get_event_loop()
    screenshot_path = await loop.run_in_executor(executor, crawler.fetch_and_screenshot, keyword)
    print(f"[파이프라인] 스크린샷 저장 완료: {screenshot_path}")
    
    # 2단계: 스크린샷 생성 완료
    await broadcast_status(keyword, "스크린샷 생성 완료", 2, 3)
    await asyncio.sleep(0.5)  # 상태 전송 대기
    
    # 3단계: AI 평가 진행중
    await broadcast_status(keyword, "AI 평가 진행중", 3, 3)
    await asyncio.sleep(0.5)  # 상태 전송 대기
    
    print(f"[파이프라인] GPT 평가 시작")
    # GPT 평가 작업을 스레드 풀에서 실행
    metrics = await loop.run_in_executor(executor, gpt_evaluator.evaluate, screenshot_path)
    print(f"[파이프라인] GPT 평가 완료: {metrics}")
    
    # 완료 상태 전송
    await broadcast_status(keyword, "평가 완료", 3, 3)
    await asyncio.sleep(0.5)  # 상태 전송 대기
    
    # 메트릭 업데이트
    metrics_manager.update_metrics(
        keyword,
        ndcg10=metrics["ndcg@10"],
        precision=metrics["precision"],
        recall=metrics["recall"],
        screenshot_path=screenshot_path,
        ndcg_reason=metrics.get("ndcg_reason", ""),
        precision_reason=metrics.get("precision_reason", ""),
        recall_reason=metrics.get("recall_reason", "")
    )
    print(f"[파이프라인] 메트릭 업데이트 완료: {keyword}")
    
    # 완료 후 최종 결과 브로드캐스트
    await broadcast_update()

@router.get("/api/metrics")
async def get_metrics():
    return {
        "status": "success",
        "data": metrics_manager.get_metrics(),
        "timestamp": metrics_manager.get_last_updated()
    }

@router.post("/api/keyword")
async def post_keyword(req: KeywordRequest):
    print(f"[API] 키워드 요청 수신: {req.keyword}")
    await on_keyword_message(req.keyword)
    return {"status": "success", "keyword": req.keyword}

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_connections.append(websocket)
    print(f"[WebSocket] 새 연결 추가. 총 연결 수: {len(websocket_connections)}")
    
    # 연결 시 현재 데이터 전송
    try:
        await websocket.send_json({
            "metrics": metrics_manager.get_metrics(),
            "timestamp": metrics_manager.get_last_updated()
        })
        print("[WebSocket] 초기 데이터 전송 완료")
        
        # 연결 유지
        while True:
            await asyncio.sleep(10)  # ping 간격 늘림
            
    except Exception as e:
        print(f"[WebSocket] 연결 에러: {e}")
    finally:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)
        print(f"[WebSocket] 연결 종료. 남은 연결 수: {len(websocket_connections)}")

# 스크린샷 static 서빙
screenshot_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../screenshot"))
@router.get("/screenshot/{filename}")
async def get_screenshot(filename: str):
    file_path = os.path.join(screenshot_dir, filename)
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": "File not found"})
    return FileResponse(file_path) 