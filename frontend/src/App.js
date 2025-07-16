import React, { useEffect, useState } from "react";
import {
  getMetrics,
  subscribeMetrics,
  postKeyword,
} from "./services/metricsApi";
import MetricsTable from "./components/MetricsTable";
import ScreenshotModal from "./components/ScreenshotModal";
import "./App.css";

function App() {
  const [metrics, setMetrics] = useState({});
  const [timestamp, setTimestamp] = useState("");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [statusUpdates, setStatusUpdates] = useState({});
  const [selectedScreenshot, setSelectedScreenshot] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    // 최초 데이터 fetch
    getMetrics().then((res) => {
      setMetrics((prev) => ({ ...prev, ...res.data }));
      setTimestamp(res.timestamp);
    });

    // WebSocket 구독 - 실시간 업데이트
    const ws = subscribeMetrics((data) => {
      console.log("WebSocket 업데이트 수신:", data);
      console.log("현재 metrics 상태:", metrics);

      if (data.type === "status") {
        // 상태 업데이트 처리
        setStatusUpdates((prev) => ({
          ...prev,
          [data.keyword]: {
            status: data.status,
            step: data.step,
            total_steps: data.total_steps,
            timestamp: data.timestamp,
          },
        }));
        // 완료 또는 실패 시 입력 가능하게
        if (data.status.includes("완료") || data.status.includes("실패")) {
          setLoading(false);
        }
      } else if (data.type === "metric_update") {
        // 개별 메트릭 실시간 업데이트 - 새로운 구조 처리
        console.log("metric_update 수신:", data.keyword, data.metrics);
        if (data.keyword && data.metrics) {
          setMetrics((prev) => {
            const newMetrics = {
              ...prev,
              [data.keyword]: data.metrics, // { musinsa: {...}, 29cm: {...} } 구조
            };
            console.log("새로운 metrics 상태:", newMetrics);
            return newMetrics;
          });

          // 완료된 키워드의 진행 상태 제거
          setStatusUpdates((prev) => {
            const newStatus = { ...prev };
            delete newStatus[data.keyword];
            return newStatus;
          });
        }
      } else {
        // 전체 메트릭 업데이트 - 새로운 구조 처리
        console.log("전체 메트릭 업데이트 수신:", data.metrics);
        if (data.metrics) {
          setMetrics(data.metrics); // { keyword: { musinsa: {...}, 29cm: {...} } } 구조
        }
        setTimestamp(data.timestamp);

        // 완료된 키워드의 상태 제거
        if (data.metrics) {
          setStatusUpdates((prev) => {
            const newStatus = { ...prev };
            Object.keys(data.metrics).forEach((keyword) => {
              delete newStatus[keyword];
            });
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
    } catch (err) {
      setError("키워드 전송 실패");
    } finally {
      setLoading(false);
    }
  };

  const handleScreenshotClick = (screenshot) => {
    setSelectedScreenshot(screenshot);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setSelectedScreenshot(null);
  };

  return (
    <div className="app">
      <div className="app-container">
        <header className="app-header">
          <h1 className="app-title">
            무신사/29CM 키워드 검색품질지표 깨부시자
          </h1>
          <p className="app-subtitle">AI 기반 검색 품질 평가 시스템</p>
        </header>

        <div className="search-section">
          <form onSubmit={handleSubmit} className="search-form">
            <div className="search-input-wrapper">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="키워드를 입력하세요 (예: 반팔티, 청바지, 운동화)"
                className="search-input"
                disabled={loading}
              />
              <button
                type="submit"
                className="search-button"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <span className="loading-spinner"></span>
                    처리 중...
                  </>
                ) : (
                  "검색"
                )}
              </button>
            </div>
          </form>
          {error && <div className="error-message">{error}</div>}
        </div>

        {/* 진행 상황 표시 */}
        {Object.keys(statusUpdates).length > 0 && (
          <div className="progress-section">
            <h3 className="progress-title">
              <span className="progress-icon">🔄</span>
              진행 상황
            </h3>
            <div className="progress-list">
              {Object.entries(statusUpdates).map(([keyword, status]) => (
                <div key={keyword} className="progress-item">
                  <div className="progress-header">
                    <span className="progress-keyword">📝 {keyword}</span>
                    <span className="progress-status">{status.status}</span>
                  </div>
                  <div className="progress-bar-container">
                    <div
                      className={`progress-bar ${
                        status.step === status.total_steps ? "completed" : ""
                      }`}
                      style={{
                        width: `${(status.step / status.total_steps) * 100}%`,
                      }}
                    ></div>
                    <span className="progress-text">
                      {Math.round((status.step / status.total_steps) * 100)}% (
                      {status.step}/{status.total_steps})
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="content-section">
          <div className="timestamp">최종 갱신: {timestamp}</div>
          <MetricsTable
            metrics={metrics}
            onScreenshotClick={handleScreenshotClick}
          />
        </div>
      </div>

      {isModalOpen && selectedScreenshot && (
        <ScreenshotModal screenshot={selectedScreenshot} onClose={closeModal} />
      )}
    </div>
  );
}

export default App;
