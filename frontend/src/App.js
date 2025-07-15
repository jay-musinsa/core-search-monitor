import React, { useEffect, useState } from "react";
import { getMetrics, subscribeMetrics, postKeyword } from "./services/metricsApi";
import MetricsTable from "./components/MetricsTable";

function App() {
  const [metrics, setMetrics] = useState({});
  const [timestamp, setTimestamp] = useState("");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [statusUpdates, setStatusUpdates] = useState({}); // 키워드별 상태 저장

  // 상태 업데이트 디버깅
  useEffect(() => {
    console.log("StatusUpdates 변경됨:", statusUpdates);
  }, [statusUpdates]);

  useEffect(() => {
    // 최초 데이터 fetch
    getMetrics().then((res) => {
      setMetrics(res.data);
      setTimestamp(res.timestamp);
    });
    
    // WebSocket 구독 - 실시간 업데이트만 받음
    const ws = subscribeMetrics((data) => {
      console.log("WebSocket 업데이트 수신:", data);
      
      if (data.type === "status") {
        console.log("상태 업데이트:", data);
        // 상태 업데이트 처리
        setStatusUpdates(prev => {
          const newStatus = {
            ...prev,
            [data.keyword]: {
              status: data.status,
              step: data.step,
              total_steps: data.total_steps,
              timestamp: data.timestamp
            }
          };
          console.log("새로운 상태:", newStatus);
          return newStatus;
        });
      } else {
        console.log("메트릭 업데이트:", data);
        // 메트릭 업데이트 처리
        setMetrics(data.metrics);
        setTimestamp(data.timestamp);
        // 완료된 키워드의 상태 제거
        if (data.metrics) {
          setStatusUpdates(prev => {
            const newStatus = { ...prev };
            Object.keys(data.metrics).forEach(keyword => {
              delete newStatus[keyword];
            });
            console.log("상태 제거 후:", newStatus);
            return newStatus;
          });
        }
      }
    });
    
    return () => ws.close();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    setLoading(true);
    setError("");
    try {
      await postKeyword(input.trim());
      setInput("");
      // HTTP 요청 완료 후 WebSocket으로 자동 업데이트됨
    } catch (err) {
      setError("키워드 전송 실패");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: "40px auto", fontFamily: "sans-serif" }}>
      <h1>무신사 키워드 검색품질지표 깨부시자</h1>
      <form onSubmit={handleSubmit} style={{ marginBottom: 20 }}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="키워드를 입력하세요"
          style={{ fontSize: 18, padding: 8, width: 300 }}
          disabled={loading}
        />
        <button type="submit" style={{ fontSize: 18, marginLeft: 8 }} disabled={loading}>
          {loading ? "처리 중..." : "검색"}
        </button>
      </form>
      {error && <div style={{ color: "red", marginBottom: 10 }}>{error}</div>}
      
      {/* 상태 업데이트 표시 */}
      {Object.keys(statusUpdates).length > 0 && (
        <div style={{ 
          marginBottom: 20, 
          padding: 15, 
          backgroundColor: "#f8f9fa", 
          border: "2px solid #007bff", 
          borderRadius: 8,
          boxShadow: "0 2px 4px rgba(0,0,0,0.1)"
        }}>
          <h3 style={{ margin: "0 0 15px 0", color: "#007bff", fontSize: 18 }}>🔄 진행 상황</h3>
          {Object.entries(statusUpdates).map(([keyword, status]) => (
            <div key={keyword} style={{ 
              marginBottom: 15, 
              padding: 10, 
              backgroundColor: "white", 
              borderRadius: 5,
              border: "1px solid #dee2e6"
            }}>
              <div style={{ fontWeight: "bold", marginBottom: 8, color: "#333", fontSize: 16 }}>
                📝 키워드: {keyword}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 15 }}>
                <div style={{ 
                  width: 250, 
                  height: 25, 
                  backgroundColor: "#e9ecef", 
                  borderRadius: 12,
                  overflow: "hidden",
                  position: "relative"
                }}>
                  <div style={{
                    width: `${(status.step / status.total_steps) * 100}%`,
                    height: "100%",
                    backgroundColor: status.step === status.total_steps ? "#28a745" : "#007bff",
                    transition: "width 0.5s ease",
                    borderRadius: 12
                  }}></div>
                  <div style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 12,
                    fontWeight: "bold",
                    color: status.step > 1 ? "white" : "#666"
                  }}>
                    {Math.round((status.step / status.total_steps) * 100)}%
                  </div>
                </div>
                <span style={{ 
                  fontSize: 14, 
                  color: "#495057",
                  fontWeight: "500",
                  minWidth: 200
                }}>
                  {status.status} ({status.step}/{status.total_steps})
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
      
      <div style={{ color: "#888", fontSize: 14 }}>최종 갱신: {timestamp}</div>
      <MetricsTable metrics={metrics} />
    </div>
  );
}

export default App;
