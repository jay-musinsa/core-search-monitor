import React from "react";
import "./QualityMetricsCard.css";

const QualityMetricsCard = ({ title, value, format, color }) => {
  const formatValue = (value, format) => {
    if (format === "decimal") {
      return value.toFixed(3);
    } else if (format === "percentage") {
      return `${(value * 100).toFixed(1)}%`;
    } else if (format === "integer") {
      return value.toLocaleString();
    }
    return value;
  };

  return (
    <div className="quality-metrics-card">
      <div className="card-header">
        <h3 className="card-title">{title}</h3>
      </div>
      <div className="card-content">
        <div className="metric-value" style={{ color }}>
          {formatValue(value, format)}
        </div>
      </div>
    </div>
  );
};

export default QualityMetricsCard;
