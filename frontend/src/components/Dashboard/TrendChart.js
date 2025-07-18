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
import { Typography, Empty } from "antd";

const { Title, Text } = Typography;

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
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="표시할 트렌드 데이터가 없습니다"
      />
    );
  }

  return (
    <div>
      <div className="mb-4">
        <div className="flex justify-between items-center">
          <Title level={4} className="mb-0">품질 트렌드</Title>
          <div className="text-sm text-gray-600">
            <Text>
              기간:{" "}
              {dateRange === "1d"
                ? "1일"
                : dateRange === "7d"
                ? "7일"
                : dateRange === "30d"
                ? "30일"
                : "90일"}
            </Text>
            {platform !== "all" && <Text> | 플랫폼: {platform}</Text>}
          </div>
        </div>
      </div>

      <div className="w-full">
        <ResponsiveContainer width="100%" height={350}>
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
