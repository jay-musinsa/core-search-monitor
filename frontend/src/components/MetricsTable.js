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
      <div className="flex justify-center items-center min-h-[300px] bg-white border border-gray-200 rounded-lg">
        <div className="text-center text-gray-500">
          <div className="text-6xl mb-4">📊</div>
          <Title level={4} className="text-gray-500 mb-2">
            검색 결과가 없습니다
          </Title>
          <Text className="text-gray-400">
            키워드를 입력하여 검색을 시작하세요
          </Text>
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

  const getPlatformTag = (platform) => {
    const platformMap = {
      musinsa: { label: "무신사", color: "default" },
      "29cm": { label: "29CM", color: "red" },
    };
    const platformInfo = platformMap[platform] || {
      label: platform,
      color: "default",
    };

    return (
      <Tag color={platformInfo.color} className="font-semibold">
        {platformInfo.label}
      </Tag>
    );
  };

  // 테이블 데이터 준비
  const tableData = Object.entries(metrics).flatMap(([keyword, platforms]) =>
    [
      ["musinsa", platforms.musinsa],
      ["29cm", platforms["29cm"]],
    ].map(([platformKey, m]) =>
      m ? {
        key: keyword + platformKey,
        keyword,
        platform: platformKey,
        ndcg: m["ndcg@10"] || 0,
        precision: m.precision || 0,
        recall: m.recall || 0,
        screenshot: m.screenshot,
        ndcg_reason: m.ndcg_reason,
        precision_reason: m.precision_reason,
        recall_reason: m.recall_reason,
        precision_issues: m.precision_issues,
        rawData: m,
      } : null
    ).filter(Boolean)
  );

  // 테이블 컬럼
  const columns = [
    {
      title: "키워드",
      dataIndex: "keyword",
      key: "keyword",
      width: 120,
      render: (text) => (
        <Text strong className="text-gray-900">
          {text}
        </Text>
      ),
    },
    {
      title: "플랫폼",
      dataIndex: "platform",
      key: "platform",
      width: 100,
      render: (platform) => getPlatformTag(platform),
    },
    {
      title: "NDCG@10",
      dataIndex: "ndcg",
      key: "ndcg",
      width: 120,
      render: (value, record) => (
        <Space direction="vertical" size="small">
          <Tag color={getScoreColor(value)} className="font-semibold w-16 text-center">
            {value.toFixed(3)}
          </Tag>
          <Text className="text-xs text-gray-500">
            {getScoreLabel(value)}
          </Text>
          {record.ndcg_reason && (
            <Tooltip title={record.ndcg_reason}>
              <Text className="text-xs text-gray-400 italic cursor-help">
                {record.ndcg_reason.length > 20 
                  ? record.ndcg_reason.substring(0, 20) + "..."
                  : record.ndcg_reason}
              </Text>
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: "Precision",
      dataIndex: "precision",
      key: "precision",
      width: 120,
      render: (value, record) => (
        <Space direction="vertical" size="small">
          <Tag color={getScoreColor(value)} className="font-semibold w-16 text-center">
            {value.toFixed(3)}
          </Tag>
          <Text className="text-xs text-gray-500">
            {getScoreLabel(value)}
          </Text>
          {record.precision_reason && (
            <Tooltip title={record.precision_reason}>
              <Text className="text-xs text-gray-400 italic cursor-help">
                {record.precision_reason.length > 20 
                  ? record.precision_reason.substring(0, 20) + "..."
                  : record.precision_reason}
              </Text>
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: "Recall",
      dataIndex: "recall",
      key: "recall",
      width: 120,
      render: (value, record) => (
        <Space direction="vertical" size="small">
          <Tag color={getScoreColor(value)} className="font-semibold w-16 text-center">
            {value.toFixed(3)}
          </Tag>
          <Text className="text-xs text-gray-500">
            {getScoreLabel(value)}
          </Text>
          {record.recall_reason && (
            <Tooltip title={record.recall_reason}>
              <Text className="text-xs text-gray-400 italic cursor-help">
                {record.recall_reason.length > 20 
                  ? record.recall_reason.substring(0, 20) + "..."
                  : record.recall_reason}
              </Text>
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: "스크린샷",
      dataIndex: "screenshot",
      key: "screenshot",
      width: 100,
      align: "center",
      render: (screenshot, record) => (
        screenshot ? (
          <div 
            className="cursor-pointer hover:scale-105 transition-transform"
            onClick={() =>
              onScreenshotClick({
                url: `${BACKEND_URL}${
                  screenshot.startsWith("/")
                    ? screenshot
                    : "/" + screenshot
                }`,
                keyword: record.keyword,
                platform: record.platform === "musinsa" ? "무신사" : "29CM",
              })
            }
          >
            <Image
              width={60}
              height={60}
              src={`${BACKEND_URL}${
                screenshot.startsWith("/")
                  ? screenshot
                  : "/" + screenshot
              }`}
              alt={`${record.keyword} ${record.platform} 스크린샷`}
              className="rounded border border-gray-200 object-cover"
              preview={false}
            />
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center w-15 h-15 bg-gray-100 rounded border border-gray-200">
            <PictureOutlined className="text-gray-400 mb-1" />
            <Text className="text-xs text-gray-400">없음</Text>
          </div>
        )
      ),
    },
    {
      title: "상세 분석",
      key: "analysis",
      width: 120,
      align: "center",
      render: (_, record) => (
        <Button
          size="small"
          type="primary"
          ghost
          icon={<EyeOutlined />}
          onClick={() => handleAnalysisClick(record.keyword, record.platform, record.rawData)}
          className="flex items-center gap-1"
        >
          자세히 보기
        </Button>
      ),
    },
  ];

  return (
    <>
      <div className="w-full bg-white rounded-lg border border-gray-200 overflow-hidden">
        <Table
          columns={columns}
          dataSource={tableData}
          pagination={false}
          scroll={{ x: true }}
          className="w-full"
          size="middle"
          rowClassName="hover:bg-gray-50 transition-colors"
        />
      </div>

      {/* 분석 모달 */}
      <Modal
        title={selectedAnalysis ? `상세 분석 - ${selectedAnalysis.keyword} (${selectedAnalysis.platform === "musinsa" ? "무신사" : "29CM"})` : ""}
        open={showAnalysisModal}
        onCancel={closeAnalysisModal}
        footer={null}
        width={800}
        className="analysis-modal"
      >
        {selectedAnalysis && (
          <div className="space-y-6">
            <Card className="bg-gray-50">
              <Title level={4} className="mb-4">
                평가 요약
              </Title>
              <Space direction="vertical" className="w-full" size="middle">
                <div className="flex items-center gap-4 p-3 bg-white rounded border">
                  <Text strong className="min-w-[80px] text-gray-600">
                    NDCG@10:
                  </Text>
                  <Tag color={getScoreColor(selectedAnalysis.data["ndcg@10"] || 0)} className="font-semibold">
                    {(selectedAnalysis.data["ndcg@10"] || 0).toFixed(3)}
                  </Tag>
                  <Text className="text-sm text-gray-500 italic flex-1">
                    {selectedAnalysis.data.ndcg_reason}
                  </Text>
                </div>
                <div className="flex items-center gap-4 p-3 bg-white rounded border">
                  <Text strong className="min-w-[80px] text-gray-600">
                    Precision:
                  </Text>
                  <Tag color={getScoreColor(selectedAnalysis.data.precision || 0)} className="font-semibold">
                    {(selectedAnalysis.data.precision || 0).toFixed(3)}
                  </Tag>
                  <Text className="text-sm text-gray-500 italic flex-1">
                    {selectedAnalysis.data.precision_reason}
                  </Text>
                </div>
                <div className="flex items-center gap-4 p-3 bg-white rounded border">
                  <Text strong className="min-w-[80px] text-gray-600">
                    Recall:
                  </Text>
                  <Tag color={getScoreColor(selectedAnalysis.data.recall || 0)} className="font-semibold">
                    {(selectedAnalysis.data.recall || 0).toFixed(3)}
                  </Tag>
                  <Text className="text-sm text-gray-500 italic flex-1">
                    {selectedAnalysis.data.recall_reason}
                  </Text>
                </div>
              </Space>
            </Card>

            {selectedAnalysis.data.precision_issues &&
            selectedAnalysis.data.precision_issues.length > 0 ? (
              <Card>
                <Title level={4} className="mb-4">
                  <Badge count={selectedAnalysis.data.precision_issues.length} className="mr-2">
                    <span>Precision 이슈 상품들</span>
                  </Badge>
                </Title>
                <Space direction="vertical" className="w-full" size="middle">
                  {selectedAnalysis.data.precision_issues.map(
                    (issue, index) => (
                      <div key={index} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                        <div className="flex gap-4 items-start">
                          <div className="flex-shrink-0">
                            {issue.image_url && issue.image_url !== "N/A" ? (
                              <Image
                                width={80}
                                height={80}
                                src={issue.image_url}
                                alt={issue.goods_name}
                                className="rounded border border-gray-200 object-cover"
                                preview={false}
                              />
                            ) : (
                              <div className="w-20 h-20 bg-gray-100 rounded border border-gray-200 flex flex-col items-center justify-center">
                                <PictureOutlined className="text-gray-400 mb-1" />
                                <Text className="text-xs text-gray-400">이미지 없음</Text>
                              </div>
                            )}
                          </div>
                          <div className="flex-1">
                            <div className="mb-2">
                              <Text className="text-xs text-gray-500">
                                상품번호: {issue.goods_no}
                              </Text>
                              <br />
                              <Text strong className="text-gray-900">
                                {issue.goods_name}
                              </Text>
                            </div>
                            <Text className="text-sm text-gray-600 italic">
                              {issue.reason}
                            </Text>
                          </div>
                        </div>
                      </div>
                    )
                  )}
                </Space>
              </Card>
            ) : (
              <Card>
                <Title level={4} className="mb-4">
                  Precision 이슈
                </Title>
                <div className="text-center py-8">
                  <div className="text-4xl mb-2">✓</div>
                  <Text className="text-gray-500">
                    관련성 문제가 있는 상품이 없습니다. 모든 상품이 검색 키워드와 관련성이 높습니다.
                  </Text>
                </div>
              </Card>
            )}
          </div>
        )}
      </Modal>
    </>
  );
}