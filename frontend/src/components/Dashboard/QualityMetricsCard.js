import React from "react";
import { Card, Statistic, Typography } from "antd";
import { safeToFixed, safeToPercent, safeNumber } from "../../utils/formatters";

const { Text } = Typography;

const formatValue = (value, type = "number") => {
  if (type === "percentage") {
    return safeToPercent(value, 1);
  }
  return safeToFixed(value, 3);
};

const QualityMetricsCard = ({ title, value, format, color }) => {
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
