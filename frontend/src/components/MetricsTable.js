import React from "react";

const BACKEND_URL = "http://localhost:8000";

export default function MetricsTable({ metrics }) {
  if (!metrics || Object.keys(metrics).length === 0) return <div>데이터 없음</div>;
  return (
    <table border="1" cellPadding="8" style={{ width: "100%", marginTop: 20 }}>
      <thead>
        <tr>
          <th>키워드</th>
          <th>NDCG@10</th>
          <th>Precision</th>
          <th>Recall</th>
          <th>스크린샷</th>
        </tr>
      </thead>
      <tbody>
        {Object.entries(metrics).map(([keyword, m]) => (
          <tr key={keyword}>
            <td>{keyword}</td>
            <td>
              <div style={{ fontWeight: "bold" }}>
                {m.ndcg && m.ndcg["@10"]?.toFixed(3)}
              </div>
              {m.ndcg_reason && (
                <div style={{ fontSize: "0.8em", color: "#666", marginTop: "4px" }}>
                  {m.ndcg_reason}
                </div>
              )}
            </td>
            <td>
              <div style={{ fontWeight: "bold" }}>
                {m.precision?.toFixed(3)}
              </div>
              {m.precision_reason && (
                <div style={{ fontSize: "0.8em", color: "#666", marginTop: "4px" }}>
                  {m.precision_reason}
                </div>
              )}
            </td>
            <td>
              <div style={{ fontWeight: "bold" }}>
                {m.recall?.toFixed(3)}
              </div>
              {m.recall_reason && (
                <div style={{ fontSize: "0.8em", color: "#666", marginTop: "4px" }}>
                  {m.recall_reason}
                </div>
              )}
            </td>
            <td>
              {m.screenshot ? (
                <img
                  src={`${BACKEND_URL}${m.screenshot.startsWith("/") ? m.screenshot : "/" + m.screenshot}`}
                  alt={keyword}
                  style={{ width: 120, maxHeight: 180, objectFit: "cover" }}
                />
              ) : (
                <span style={{ color: "#aaa" }}>없음</span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
} 