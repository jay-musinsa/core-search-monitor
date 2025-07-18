import React, { useState } from "react";
import {
  Table,
  Tag,
  Button,
  Image,
  Typography,
  Space,
  Modal,
  Card,
  Tooltip,
  Badge,
} from "antd";
import { EyeOutlined, PictureOutlined } from "@ant-design/icons";

const { Text, Title } = Typography;

const BACKEND_URL = "http://localhost:8000";

export default function MetricsTable({ metrics, onScreenshotClick }) {
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);
  const [showAnalysisModal, setShowAnalysisModal] = useState(false);

  if (!metrics || Object.keys(metrics).length === 0) {
    return (
      <div className="no-data">
        <div className="no-data-content">
          <div className="no-data-icon">📊</div>
          <div className="no-data-text">검색 결과가 없습니다</div>
          <div className="no-data-subtext">
            키워드를 입력하여 검색을 시작하세요
          </div>
        </div>
      </div>
    );
  }

  const getScoreColor = (score) => {
    if (score >= 0.8) return "success";
    if (score >= 0.6) return "processing";
    if (score >= 0.4) return "warning";
    return "error";
  };

  const getScoreLabel = (score) => {
    if (score >= 0.8) return "우수";
    if (score >= 0.6) return "양호";
    if (score >= 0.4) return "보통";
    return "미흡";
  };

  const handleAnalysisClick = (keyword, platform, data) => {
    setSelectedAnalysis({ keyword, platform, data });
    setShowAnalysisModal(true);
  };

  const closeAnalysisModal = () => {
    setShowAnalysisModal(false);
    setSelectedAnalysis(null);
  };

  const getPlatformBadge = (platform) => {
    const platformMap = {
      musinsa: { label: "무신사", color: "#000" },
      "29cm": { label: "29CM", color: "#ff6b6b" },
    };
    const platformInfo = platformMap[platform] || {
      label: platform,
      color: "#6c757d",
    };

    return (
      <span
        className="platform-badge"
        style={{ backgroundColor: platformInfo.color }}
      >
        {platformInfo.label}
      </span>
    );
  };

  return (
    <>
      <div className="metrics-container">
        <div className="metrics-table-wrapper">
          <table className="metrics-table">
            <thead>
              <tr>
                <th>키워드</th>
                <th>플랫폼</th>
                <th>NDCG@10</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>스크린샷</th>
                <th>상세 분석</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(metrics).flatMap(([keyword, platforms]) =>
                [
                  ["musinsa", platforms.musinsa],
                  ["29cm", platforms["29cm"]],
                ].map(([platformKey, m]) =>
                  m ? (
                    <tr key={keyword + platformKey} className="metric-row">
                      <td className="keyword-cell">{keyword}</td>
                      <td className="platform-cell">
                        {getPlatformBadge(platformKey)}
                      </td>
                      <td className="metric-cell">
                        <div className="metric-score">
                          <span
                            className={`score-value ${getScoreColor(
                              m["ndcg@10"] || 0
                            )}`}
                          >
                            {(m["ndcg@10"] || 0).toFixed(3)}
                          </span>
                          <span
                            className={`score-label ${getScoreColor(
                              m["ndcg@10"] || 0
                            )}`}
                          >
                            {getScoreLabel(m["ndcg@10"] || 0)}
                          </span>
                        </div>
                        {m.ndcg_reason && (
                          <div className="metric-reason">{m.ndcg_reason}</div>
                        )}
                      </td>
                      <td className="metric-cell">
                        <div className="metric-score">
                          <span
                            className={`score-value ${getScoreColor(
                              m.precision || 0
                            )}`}
                          >
                            {(m.precision || 0).toFixed(3)}
                          </span>
                          <span
                            className={`score-label ${getScoreColor(
                              m.precision || 0
                            )}`}
                          >
                            {getScoreLabel(m.precision || 0)}
                          </span>
                        </div>
                        {m.precision_reason && (
                          <div className="metric-reason">
                            {m.precision_reason}
                          </div>
                        )}
                      </td>
                      <td className="metric-cell">
                        <div className="metric-score">
                          <span
                            className={`score-value ${getScoreColor(
                              m.recall || 0
                            )}`}
                          >
                            {(m.recall || 0).toFixed(3)}
                          </span>
                          <span
                            className={`score-label ${getScoreColor(
                              m.recall || 0
                            )}`}
                          >
                            {getScoreLabel(m.recall || 0)}
                          </span>
                        </div>
                        {m.recall_reason && (
                          <div className="metric-reason">{m.recall_reason}</div>
                        )}
                      </td>
                      <td className="screenshot-cell">
                        {m.screenshot ? (
                          <div
                            className="screenshot-container"
                            onClick={() =>
                              onScreenshotClick({
                                url: `${BACKEND_URL}${
                                  m.screenshot.startsWith("/")
                                    ? m.screenshot
                                    : "/" + m.screenshot
                                }`,
                                keyword: keyword,
                                platform:
                                  platformKey === "musinsa" ? "무신사" : "29CM",
                              })
                            }
                          >
                            <img
                              src={`${BACKEND_URL}${
                                m.screenshot.startsWith("/")
                                  ? m.screenshot
                                  : "/" + m.screenshot
                              }`}
                              alt={`${keyword} ${platformKey} 스크린샷`}
                              className="screenshot-thumbnail"
                            />
                            <div className="screenshot-overlay">
                              <span className="screenshot-icon">🔍</span>
                              <span className="screenshot-text">확대보기</span>
                            </div>
                          </div>
                        ) : (
                          <div className="no-screenshot">
                            <span className="no-screenshot-icon">📷</span>
                            <span className="no-screenshot-text">없음</span>
                          </div>
                        )}
                      </td>
                      <td className="analysis-cell">
                        <button
                          className="analysis-btn"
                          onClick={() =>
                            handleAnalysisClick(keyword, platformKey, m)
                          }
                          title="상세 분석 보기"
                        >
                          자세히 보기
                        </button>
                      </td>
                    </tr>
                  ) : null
                )
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 분석 모달 */}
      {showAnalysisModal && selectedAnalysis && (
        <div className="analysis-modal-backdrop" onClick={closeAnalysisModal}>
          <div
            className="analysis-modal-container"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="analysis-modal-header">
              <h3>
                상세 분석 - {selectedAnalysis.keyword} (
                {selectedAnalysis.platform === "musinsa" ? "무신사" : "29CM"})
              </h3>
              <button
                className="analysis-modal-close"
                onClick={closeAnalysisModal}
              >
                ×
              </button>
            </div>
            <div className="analysis-modal-content">
              <div className="analysis-section">
                <h4>평가 요약</h4>
                <div className="analysis-metrics">
                  <div className="analysis-metric">
                    <span className="metric-label">NDCG@10:</span>
                    <span className="metric-value">
                      {(selectedAnalysis.data["ndcg@10"] || 0).toFixed(3)}
                    </span>
                    <span className="metric-reason">
                      {selectedAnalysis.data.ndcg_reason}
                    </span>
                  </div>
                  <div className="analysis-metric">
                    <span className="metric-label">Precision:</span>
                    <span className="metric-value">
                      {(selectedAnalysis.data.precision || 0).toFixed(3)}
                    </span>
                    <span className="metric-reason">
                      {selectedAnalysis.data.precision_reason}
                    </span>
                  </div>
                  <div className="analysis-metric">
                    <span className="metric-label">Recall:</span>
                    <span className="metric-value">
                      {(selectedAnalysis.data.recall || 0).toFixed(3)}
                    </span>
                    <span className="metric-reason">
                      {selectedAnalysis.data.recall_reason}
                    </span>
                  </div>
                </div>
              </div>

              {selectedAnalysis.data.precision_issues &&
              selectedAnalysis.data.precision_issues.length > 0 ? (
                <div className="analysis-section">
                  <h4>Precision 이슈 상품들</h4>
                  <div className="precision-issues">
                    {selectedAnalysis.data.precision_issues.map(
                      (issue, index) => (
                        <div key={index} className="precision-issue">
                          <div className="issue-content">
                            <div className="issue-image-container">
                              {issue.image_url && issue.image_url !== "N/A" ? (
                                <img
                                  src={issue.image_url}
                                  alt={issue.goods_name}
                                  className="issue-thumbnail"
                                  onError={(e) => {
                                    e.target.style.display = "none";
                                    e.target.nextSibling.style.display = "flex";
                                  }}
                                />
                              ) : null}
                              <div className="issue-no-image">
                                <span>🖼️</span>
                                <span>이미지 없음</span>
                              </div>
                            </div>
                            <div className="issue-details">
                              <div className="issue-header">
                                <span className="issue-goods-no">
                                  상품번호: {issue.goods_no}
                                </span>
                                <span className="issue-goods-name">
                                  {issue.goods_name}
                                </span>
                              </div>
                              <div className="issue-reason">{issue.reason}</div>
                            </div>
                          </div>
                        </div>
                      )
                    )}
                  </div>
                </div>
              ) : (
                <div className="analysis-section">
                  <h4>Precision 이슈</h4>
                  <p className="no-issues">
                    관련성 문제가 있는 상품이 없습니다. 모든 상품이 검색
                    키워드와 관련성이 높습니다.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
