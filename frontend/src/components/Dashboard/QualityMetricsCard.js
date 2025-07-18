import React from "react";
import { Card, Statistic } from "antd";

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
    <Card>
      <Statistic
        title={title}
        value={formatValue(value, format)}
        valueStyle={{ color }}
      />
    </Card>
  );
};

export default QualityMetricsCard;
