import React from "react";
import { Table, Tag, Empty } from "antd";

const ComparisonTable = ({
  data,
  onKeywordSelect,
  getQualityGrade,
  filters,
}) => {
  // 플랫폼 뱃지
  const getPlatformBadge = (platform) => {
    const platformMap = {
      musinsa: { label: "무신사", color: "blue" },
      "29cm": { label: "29CM", color: "red" },
      all: { label: "전체", color: "default" },
    };
    const platformInfo = platformMap[platform] || {
      label: platform,
      color: "default",
    };

    return (
      <Tag color={platformInfo.color}>
        {platformInfo.label}
      </Tag>
    );
  };

  // 점수 뱃지
  const getScoreBadge = (score, type) => {
    const grade = getQualityGrade(score);
    let color = "default";
    if (grade === "excellent") color = "green";
    else if (grade === "good") color = "blue";
    else if (grade === "average") color = "orange";
    else if (grade === "below-average") color = "red";
    else if (grade === "poor") color = "red";
    
    return <Tag color={color}>{score.toFixed(3)}</Tag>;
  };

  // 테이블 컬럼 정의
  const columns = [
    {
      title: "키워드",
      dataIndex: "keyword",
      key: "keyword",
      sorter: (a, b) => a.keyword.localeCompare(b.keyword),
      render: (text) => <span className="font-medium">{text}</span>,
    },
    {
      title: "플랫폼",
      dataIndex: "platform",
      key: "platform",
      sorter: (a, b) => a.platform.localeCompare(b.platform),
      render: (platform) => getPlatformBadge(platform),
    },
    {
      title: "NDCG 점수",
      dataIndex: "ndcg_score",
      key: "ndcg_score",
      sorter: (a, b) => a.ndcg_score - b.ndcg_score,
      defaultSortOrder: "descend",
      render: (score) => getScoreBadge(score, "ndcg"),
    },
    {
      title: "정확도",
      dataIndex: "precision",
      key: "precision",
      sorter: (a, b) => a.precision - b.precision,
      render: (score) => getScoreBadge(score, "precision"),
    },
    {
      title: "재현율",
      dataIndex: "recall",
      key: "recall",
      sorter: (a, b) => a.recall - b.recall,
      render: (score) => getScoreBadge(score, "recall"),
    },
    {
      title: "평가일",
      dataIndex: "assessment_date",
      key: "assessment_date",
      sorter: (a, b) => new Date(a.assessment_date) - new Date(b.assessment_date),
      render: (date) => date ? new Date(date).toLocaleDateString() : "-",
    },
  ];

  if (!data || data.length === 0) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="품질 데이터가 없습니다"
      />
    );
  }

  return (
    <Table
      columns={columns}
      dataSource={data}
      rowKey={(record) => record.id || record.keyword}
      pagination={{
        pageSize: 10,
        showSizeChanger: true,
        showQuickJumper: true,
        showTotal: (total) => `총 ${total}개`,
      }}
      onRow={(record) => ({
        onClick: () => onKeywordSelect && onKeywordSelect(record),
        style: { cursor: "pointer" },
      })}
      size="middle"
      scroll={{ x: 800 }}
    />
  );
};

export default ComparisonTable;
