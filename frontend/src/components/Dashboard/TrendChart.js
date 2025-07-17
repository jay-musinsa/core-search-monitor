import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import "./TrendChart.css";

const TrendChart = ({ data = [], dateRange = "7d", platform = "all" }) => {
  // 차트 데이터 가공
  const processChartData = (rawData) => {
    if (!rawData || rawData.length === 0) return [];

    return rawData.map((item) => ({
      date: item.date ? new Date(item.date).toLocaleDateString() : "",
      ndcg_score: parseFloat(item.ndcg_score) || 0,
      precision: parseFloat(item.precision) || 0,
      recall: parseFloat(item.recall) || 0,
    }));
  };

  // 메트릭 색상 매핑
  const metricColors = {
    ndcg_score: "#1976d2",
    precision: "#388e3c",
    recall: "#f57c00",
  };

  // 메트릭 이름 매핑
  const metricLabels = {
    ndcg_score: "NDCG 점수",
    precision: "정확도",
    recall: "재현율",
  };

  // 툴팁 커스텀 포맷터
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="custom-tooltip">
          <p className="tooltip-label">{`날짜: ${label}`}</p>
          {payload.map((entry, index) => (
            <p
              key={index}
              className="tooltip-item"
              style={{ color: entry.color }}
            >
              {`${metricLabels[entry.dataKey]}: ${entry.value.toFixed(3)}`}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  // 데이터 처리
  const chartData = processChartData(data);

  // 빈 데이터 처리
  if (!chartData || chartData.length === 0) {
    return (
      <div className="trend-chart-container">
        <div className="chart-header">
          <h3>품질 트렌드</h3>
        </div>
        <div className="no-data-message">
          <p>📊 표시할 트렌드 데이터가 없습니다.</p>
          <p>데이터가 수집되면 여기에 트렌드 차트가 표시됩니다.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="trend-chart-container">
      <div className="chart-header">
        <h3>품질 트렌드</h3>
        <div className="chart-info">
          <span>
            기간:{" "}
            {dateRange === "1d"
              ? "1일"
              : dateRange === "7d"
              ? "7일"
              : dateRange === "30d"
              ? "30일"
              : "90일"}
          </span>
          {platform !== "all" && <span> | 플랫폼: {platform}</span>}
        </div>
      </div>

      <div className="chart-wrapper">
        <ResponsiveContainer width="100%" height={220}>
          <LineChart
            data={chartData}
            margin={{ top: 15, right: 20, left: 15, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11 }}
              angle={-45}
              textAnchor="end"
              height={50}
            />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Line
              type="monotone"
              dataKey="ndcg_score"
              stroke={metricColors.ndcg_score}
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 4 }}
              name={metricLabels.ndcg_score}
            />
            <Line
              type="monotone"
              dataKey="precision"
              stroke={metricColors.precision}
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 4 }}
              name={metricLabels.precision}
            />
            <Line
              type="monotone"
              dataKey="recall"
              stroke={metricColors.recall}
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 4 }}
              name={metricLabels.recall}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default TrendChart;
