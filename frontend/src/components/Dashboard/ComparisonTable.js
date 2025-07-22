import React, { useState } from "react";
import {
  Table,
  Tag,
  Button,
  Typography,
  Space,
  Modal,
  Card,
  Badge,
  Tooltip,
  Image,
  Divider,
  Empty,
} from "antd";
import { EyeOutlined, PictureOutlined } from "@ant-design/icons";
import { safeToFixed, safeToPercent, safeNumber } from "../../utils/formatters";

const { Text, Title } = Typography;
const BACKEND_URL = "http://localhost:8000";

const ComparisonTable = ({
  data,
  onKeywordSelect,
  getQualityGrade,
  filters,
}) => {
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);
  const [showAnalysisModal, setShowAnalysisModal] = useState(false);

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

    return <Tag color={platformInfo.color}>{platformInfo.label}</Tag>;
  };

  // 점수 뱃지
  const getScoreBadge = (score, type) => {
    // score가 undefined이거나 null인 경우 처리
    if (score === undefined || score === null || isNaN(score)) {
      return <Tag color="default">-</Tag>;
    }

    const grade = getQualityGrade(score);
    let color = "default";
    if (grade === "excellent") color = "green";
    else if (grade === "good") color = "blue";
    else if (grade === "average") color = "orange";
    else if (grade === "below-average") color = "red";
    else if (grade === "poor") color = "red";

    return <Tag color={color}>{score.toFixed(3)}</Tag>;
  };

  // 신뢰도 색상 계산
  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return "#52c41a";
    if (confidence >= 0.6) return "#1890ff";
    if (confidence >= 0.4) return "#faad14";
    return "#f5222d";
  };

  // 평가 방법 뱃지
  const getEvaluationMethodBadge = (method, confidence) => {
    const color = getConfidenceColor(confidence);
    const methodNames = {
      Composite: "종합",
      "LLM-gpt-4o": "GPT-4",
      "Rule-Based": "규칙",
      "Keyword-Based": "키워드",
      "Embedding-sentence-transformers": "임베딩",
    };

    return (
      <Badge
        color={color}
        text={methodNames[method] || method}
        style={{ fontSize: "12px" }}
      />
    );
  };

  // 분석 상세 보기
  const handleAnalysisClick = (keyword, platform, data) => {
    setSelectedAnalysis({ keyword, platform, data });
    setShowAnalysisModal(true);
  };

  const closeAnalysisModal = () => {
    setShowAnalysisModal(false);
    setSelectedAnalysis(null);
  };

  // 스크린샷 처리
  const handleScreenshotClick = (screenshotPath) => {
    if (screenshotPath && screenshotPath !== "N/A") {
      const imageUrl = screenshotPath.startsWith("http")
        ? screenshotPath
        : `${BACKEND_URL}${screenshotPath}`;
      window.open(imageUrl, "_blank");
    }
  };

  // 테이블 컬럼 정의
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
      width: 80,
      render: (platform) => getPlatformBadge(platform),
    },
    {
      title: "NDCG@10",
      dataIndex: "ndcg_score",
      key: "ndcg_score",
      width: 100,
      render: (score) => getScoreBadge(score, "ndcg"),
      sorter: (a, b) => (a.ndcg_score || 0) - (b.ndcg_score || 0),
    },
    {
      title: "Precision",
      dataIndex: "precision",
      key: "precision",
      width: 100,
      render: (score) => getScoreBadge(score, "precision"),
      sorter: (a, b) => (a.precision || 0) - (b.precision || 0),
    },
    {
      title: "Recall",
      dataIndex: "recall",
      key: "recall",
      width: 100,
      render: (score) => getScoreBadge(score, "recall"),
      sorter: (a, b) => (a.recall || 0) - (b.recall || 0),
    },
    {
      title: "평가방법",
      dataIndex: "evaluation_method",
      key: "evaluation_method",
      width: 100,
      render: (method, record) =>
        getEvaluationMethodBadge(method, record.confidence || 0),
    },
    {
      title: "신뢰도",
      dataIndex: "confidence",
      key: "confidence",
      width: 90,
      render: (confidence) => {
        if (confidence === undefined || confidence === null) {
          return <Text type="secondary">-</Text>;
        }
        const color = getConfidenceColor(confidence);
        return (
          <Text style={{ color, fontWeight: "bold" }}>
            {(confidence * 100).toFixed(0)}%
          </Text>
        );
      },
      sorter: (a, b) => (a.confidence || 0) - (b.confidence || 0),
    },
    {
      title: "스크린샷",
      dataIndex: "screenshot_path",
      key: "screenshot_path",
      width: 100,
      render: (screenshot) => {
        if (!screenshot || screenshot === "N/A") {
          return <Text type="secondary">없음</Text>;
        }
        return (
          <Button
            type="link"
            icon={<PictureOutlined />}
            onClick={() => handleScreenshotClick(screenshot)}
            size="small"
          >
            보기
          </Button>
        );
      },
    },
    {
      title: "문제상품",
      dataIndex: "precision_issues",
      key: "precision_issues",
      width: 100,
      render: (issues, record) => {
        let issueCount = 0;

        // precision_issues가 문자열인 경우 JSON 파싱 시도
        if (typeof issues === "string") {
          try {
            const parsedIssues = JSON.parse(issues);
            issueCount = Array.isArray(parsedIssues) ? parsedIssues.length : 0;
          } catch (e) {
            issueCount = 0;
          }
        } else if (Array.isArray(issues)) {
          issueCount = issues.length;
        }

        if (issueCount === 0) {
          return <Text type="secondary">없음</Text>;
        }

        return (
          <Button
            type="link"
            size="small"
            onClick={() =>
              handleAnalysisClick(record.keyword, record.platform, record)
            }
          >
            {issueCount}개
          </Button>
        );
      },
    },
    {
      title: "평가일",
      dataIndex: "assessment_date",
      key: "assessment_date",
      width: 100,
      render: (date) => {
        if (!date) return <Text type="secondary">-</Text>;
        return <Text className="text-sm">{date}</Text>;
      },
      sorter: (a, b) =>
        new Date(a.assessment_date || 0) - new Date(b.assessment_date || 0),
    },
    {
      title: "작업",
      key: "actions",
      width: 80,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="상세 분석">
            <Button
              type="text"
              icon={<EyeOutlined />}
              size="small"
              onClick={() =>
                handleAnalysisClick(record.keyword, record.platform, record)
              }
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  if (!data || data.length === 0) {
    return <Empty description="키워드 데이터가 없습니다" />;
  }

  return (
    <>
      <Table
        dataSource={data}
        columns={columns}
        rowKey={(record) => `${record.keyword}-${record.platform}-${record.id}`}
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total, range) =>
            `${range[0]}-${range[1]} / 총 ${total}개`,
        }}
        scroll={{ x: 1200 }}
        size="small"
      />

      {/* 분석 상세 모달 */}
      <Modal
        title={
          selectedAnalysis ? (
            <div className="flex items-center gap-2">
              <Text strong>
                {selectedAnalysis.keyword} - {selectedAnalysis.platform}
              </Text>
              {selectedAnalysis.data?.evaluation_method &&
                getEvaluationMethodBadge(
                  selectedAnalysis.data.evaluation_method,
                  selectedAnalysis.data.confidence || 0
                )}
            </div>
          ) : (
            "상세 분석"
          )
        }
        open={showAnalysisModal}
        onCancel={closeAnalysisModal}
        footer={[
          <Button key="close" onClick={closeAnalysisModal}>
            닫기
          </Button>,
        ]}
        width={800}
      >
        {selectedAnalysis && (
          <div className="space-y-4">
            {/* 점수 요약 */}
            <Card size="small" title="평가 점수">
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {safeToFixed(selectedAnalysis.data.ndcg_score || 0, 3)}
                  </div>
                  <div className="text-sm text-gray-500">NDCG@10</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {safeToFixed(selectedAnalysis.data.precision || 0, 3)}
                  </div>
                  <div className="text-sm text-gray-500">Precision</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-600">
                    {safeToFixed(selectedAnalysis.data.recall || 0, 3)}
                  </div>
                  <div className="text-sm text-gray-500">Recall</div>
                </div>
              </div>
            </Card>

            {/* 평가 이유 */}
            {(selectedAnalysis.data.ndcg_reason ||
              selectedAnalysis.data.precision_reason ||
              selectedAnalysis.data.recall_reason) && (
              <Card size="small" title="평가 이유">
                {selectedAnalysis.data.ndcg_reason && (
                  <div className="mb-2">
                    <Text strong>NDCG: </Text>
                    <Text>{selectedAnalysis.data.ndcg_reason}</Text>
                  </div>
                )}
                {selectedAnalysis.data.precision_reason && (
                  <div className="mb-2">
                    <Text strong>Precision: </Text>
                    <Text>{selectedAnalysis.data.precision_reason}</Text>
                  </div>
                )}
                {selectedAnalysis.data.recall_reason && (
                  <div>
                    <Text strong>Recall: </Text>
                    <Text>{selectedAnalysis.data.recall_reason}</Text>
                  </div>
                )}
              </Card>
            )}

            {/* 문제 상품 목록 */}
            {selectedAnalysis?.precision_issues &&
              selectedAnalysis.precision_issues.length > 0 && (
                <Card className="mt-4">
                  <Title level={5}>
                    문제 상품 목록 ({selectedAnalysis.precision_issues.length}
                    개)
                  </Title>
                  <div className="space-y-3">
                    {selectedAnalysis.precision_issues.map((issue, idx) => (
                      <Card
                        key={idx}
                        size="small"
                        className="border-l-4 border-l-red-400"
                      >
                        <div className="flex items-start space-x-3">
                          {issue.image_url && issue.image_url !== "N/A" && (
                            <Image
                              src={issue.image_url}
                              alt={issue.goods_name}
                              width={60}
                              height={60}
                              className="rounded object-cover"
                              fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
                            />
                          )}
                          <div className="flex-1">
                            <Text strong className="text-sm">
                              {issue.goods_name}
                            </Text>
                            <br />
                            <Text className="text-xs text-gray-500">
                              상품번호: {issue.goods_no}
                            </Text>
                            <br />
                            <Text className="text-sm text-red-600 font-medium">
                              {issue.reason}
                            </Text>

                            {/* 상세 평가기별 이유 표시 */}
                            {issue.detailed_reasons &&
                              issue.detailed_reasons.length > 0 && (
                                <div className="mt-3 p-3 bg-gray-50 border-l-4 border-l-orange-400 rounded">
                                  <div className="flex items-center mb-2">
                                    <Text
                                      strong
                                      className="text-gray-700 text-sm"
                                    >
                                      📋 상세 평가 내용
                                    </Text>
                                    {issue.detailed_reasons.length > 1 && (
                                      <span className="ml-2 px-2 py-1 bg-orange-100 text-orange-700 text-xs rounded-full">
                                        {issue.detailed_reasons.length}개 평가기
                                      </span>
                                    )}
                                  </div>
                                  <div className="space-y-1">
                                    {issue.detailed_reasons.map(
                                      (detail, detailIdx) => (
                                        <div
                                          key={detailIdx}
                                          className="flex items-start text-gray-700 text-xs"
                                        >
                                          <span className="text-orange-500 mr-1">
                                            ▪
                                          </span>
                                          <span className="flex-1">
                                            {detail.replace("• ", "")}
                                          </span>
                                        </div>
                                      )
                                    )}
                                  </div>

                                  {/* 다중 평가기인 경우 추가 설명 */}
                                  {issue.detailed_reasons.length > 1 && (
                                    <div className="mt-2 pt-2 border-t border-gray-200">
                                      <Text className="text-xs text-gray-600 italic">
                                        💡 여러 평가기에서 동일한 상품의 문제를
                                        감지했습니다. 이는 해당 상품이 검색
                                        키워드와 관련성이 낮을 가능성이 높음을
                                        의미합니다.
                                      </Text>
                                    </div>
                                  )}
                                </div>
                              )}
                          </div>
                        </div>
                      </Card>
                    ))}
                  </div>
                </Card>
              )}

            {/* 스크린샷 */}
            {selectedAnalysis.data.screenshot_path &&
              selectedAnalysis.data.screenshot_path !== "N/A" && (
                <Card size="small" title="검색 결과 스크린샷">
                  <div className="text-center">
                    <Image
                      src={`${BACKEND_URL}${selectedAnalysis.data.screenshot_path}`}
                      alt="검색 결과 스크린샷"
                      style={{ maxWidth: "100%", maxHeight: "400px" }}
                      fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMIAAADDCAYAAADQvc6UAAABRWlDQ1BJQ0MgUHJvZmlsZQAAKJFjYGASSSwoyGFhYGDIzSspCnJ3UoiIjFJgf8LAwSDCIMogwMCcmFxc4BgQ4ANUwgCjUcG3awyMIPqyLsis7PPOq3QdDFcvjV3jOD1boQVTPQrgSkktTgbSf4A4LbmgqISBgTEFyFYuLykAsTuAbJEioKOA7DkgdjqEvQHEToKwj4DVhAQ5A9k3gGyB5IxEoBmML4BsnSQk8XQkNtReEOBxcfXxUQg1Mjc0dyHgXNJBSWpFCYh2zi+oLMpMzyhRcASGUqqCZ16yno6CkYGRAQMDKMwhqj/fAIcloxgHQqxAjIHBEugw5sUIsSQpBobtQPdLciLEVJYzMPBHMDBsayhILEqEO4DxG0txmrERhM29nYGBddr//5/DGRjYNRkY/l7////39v///y4Dmn+LgeHANwDrkl1AuO+pmgAAADhlWElmTU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAAqACAAQAAAABAAAAwqADAAQAAAABAAAAwwAAAAD9b/HnAAAHlklEQVR4Ae3dP3Ik1RnG4W+FgYxN"
                    />
                  </div>
                </Card>
              )}
          </div>
        )}
      </Modal>
    </>
  );
};

export default ComparisonTable;
