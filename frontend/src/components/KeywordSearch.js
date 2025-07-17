import React, { useEffect, useState } from "react";
import {
  getMetrics,
  subscribeMetrics,
  postKeyword,
} from "../services/metricsApi";
import MetricsTable from "./MetricsTable";
import ScreenshotModal from "./ScreenshotModal";
import "./KeywordSearch.css";

function KeywordSearch() {
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

        setMetrics((prev) => {
          const newMetrics = { ...prev };
          newMetrics[data.keyword] = {
            ...newMetrics[data.keyword],
            ...data.metrics,
          };
          return newMetrics;
        });
      }
    });

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    setLoading(true);
    setError("");

    try {
      const response = await postKeyword(input);
      console.log("키워드 요청 완료:", response);

      // 상태 업데이트 초기화
      setStatusUpdates({
        [input]: {
          status: "요청 처리 시작",
          step: 0,
          total_steps: 5,
          timestamp: new Date().toISOString(),
        },
      });
    } catch (err) {
      console.error("키워드 요청 실패:", err);
      setError("키워드 요청에 실패했습니다. 다시 시도해주세요.");
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

  // 데이터 새로고침
  const handleRefresh = () => {
    getMetrics().then((res) => {
      setMetrics((prev) => ({ ...prev, ...res.data }));
      setTimestamp(res.timestamp);
    });
  };

  return (
    <div className="admin-page">
      {/* Breadcrumb */}
      <nav className="breadcrumb">
        <span className="breadcrumb-item">검색품질 모니터링</span>
        <span className="breadcrumb-separator">&gt;</span>
        <span className="breadcrumb-item active">키워드 검색</span>
      </nav>

      {/* 페이지 제목 */}
      <h1 className="page-title">Keyword Search</h1>

      {/* 섹션 제목 */}
      <h2 className="section-title">검색 테스트</h2>

      {/* 검색 폼 */}
      <div className="search-section">
        <div className="search-form">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="키워드를 입력하세요 (예: 반팔티, 청바지, 운동화)"
            className="search-input"
            disabled={loading}
            onKeyPress={(e) => {
              if (e.key === "Enter") {
                handleSubmit(e);
              }
            }}
          />
          <button
            type="submit"
            className="search-button"
            disabled={loading}
            onClick={handleSubmit}
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

        {error && <div className="error-message">{error}</div>}
      </div>

      {/* 진행 상황 표시 */}
      {Object.keys(statusUpdates).length > 0 && (
        <div className="progress-section">
          <h3 className="progress-title">진행 상황</h3>
          <div className="progress-list">
            {Object.entries(statusUpdates).map(([keyword, status]) => (
              <div key={keyword} className="progress-item">
                <div className="progress-info">
                  <span className="progress-keyword">{keyword}</span>
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

      {/* 검색 결과 */}
      <div className="results-section">
        <h3 className="results-title">검색 결과</h3>
        <div className="results-meta">
          {Object.keys(metrics).length > 0
            ? `${
                Object.keys(metrics).length
              }개의 키워드 • 최종 갱신: ${timestamp}`
            : `최종 갱신: ${timestamp}`}
        </div>

        {Object.keys(metrics).length === 0 ? (
          <div className="no-results">
            <p>
              검색된 키워드가 없습니다. 위의 검색창에서 키워드를 입력하여
              테스트를 시작하세요.
            </p>
          </div>
        ) : (
          <MetricsTable
            metrics={metrics}
            onScreenshotClick={handleScreenshotClick}
          />
        )}
      </div>

      {isModalOpen && selectedScreenshot && (
        <ScreenshotModal screenshot={selectedScreenshot} onClose={closeModal} />
      )}
    </div>
  );
}

export default KeywordSearch;
