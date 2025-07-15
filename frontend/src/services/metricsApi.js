// /api/metrics REST API 호출
export async function getMetrics() {
  const res = await fetch("http://localhost:8000/api/metrics");
  if (!res.ok) throw new Error("메트릭 조회 실패");
  return await res.json();
}

// /ws WebSocket 구독
export function subscribeMetrics(onMessage) {
  const ws = new WebSocket("ws://localhost:8000/ws");
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onMessage(data);
  };
  return ws;
}

// 키워드 입력 API
export async function postKeyword(keyword) {
  const res = await fetch("http://localhost:8000/api/keyword", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keyword })
  });
  if (!res.ok) throw new Error("키워드 전송 실패");
  return await res.json();
} 