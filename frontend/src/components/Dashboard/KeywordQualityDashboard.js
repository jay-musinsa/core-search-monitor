import React, { useState, useEffect, useCallback } from "react";
import {
  Card,
  Row,
  Col,
  Statistic,
  Button,
  Space,
  Drawer,
  Typography,
  Breadcrumb,
  Spin,
  Alert,
  Divider,
  Empty,
} from "antd";
import {
  FilterOutlined,
  ReloadOutlined,
  DownloadOutlined,
  DashboardOutlined,
  RiseOutlined,
  ExclamationCircleOutlined,
} from "@ant-design/icons";
import { metricsApi } from "../../services/metricsApi";
import QualityMetricsCard from "./QualityMetricsCard";
import TrendChart from "./TrendChart";
import ComparisonTable from "./ComparisonTable";
import FilterPanel from "./FilterPanel";

const { Title, Text } = Typography;

const KeywordQualityDashboard = () => {
  const [qualityData, setQualityData] = useState([]);
  const [trendData, setTrendData] = useState([]);
  const [summaryStats, setSummaryStats] = useState({
    totalKeywords: 0,
    avgNdcgScore: 0,
    avgPrecision: 0,
    avgRecall: 0,
    anomalyCount: 0,
    lastUpdated: null,
  });
  const [filters, setFilters] = useState({
    platform: "all",
    category: "all",
    dateRange: "7d",
    threshold: 0.5,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedKeyword, setSelectedKeyword] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // 품질 데이터 조회
  const fetchQualityData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await metricsApi.getKeywordQuality({
        platform: filters.platform,
        category: filters.category,
        dateRange: filters.dateRange,
        threshold: filters.threshold,
        sortBy: "ndcg_score",
        sortDirection: "desc",
        page: 1,
        limit: 1000,
      });

      if (response.success) {
        setQualityData(response.data);
        setSummaryStats(response.summary);
      } else {
        setError(response.message || "데이터 로드 실패");
      }
    } catch (error) {
      console.error("품질 데이터 조회 실패:", error);
      setError("네트워크 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  // 트렌드 데이터 조회
  const fetchTrendData = useCallback(async () => {
    try {
      const response = await metricsApi.getTrendData({
        platform: filters.platform,
        dateRange: filters.dateRange,
      });

      if (response.success) {
        setTrendData(response.data);
      }
    } catch (error) {
      console.error("트렌드 데이터 조회 실패:", error);
    }
  }, [filters]);

  // 초기 데이터 로드
  useEffect(() => {
    fetchQualityData();
    fetchTrendData();
  }, [fetchQualityData, fetchTrendData]);

  // 필터 변경 핸들러
  const handleFilterChange = (newFilters) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
  };

  // 키워드 선택 핸들러
  const handleKeywordSelect = (keyword) => {
    setSelectedKeyword(keyword);
  };

  // 품질 등급 계산
  const getQualityGrade = (score) => {
    if (score >= 0.9) return "excellent";
    if (score >= 0.8) return "good";
    if (score >= 0.7) return "average";
    if (score >= 0.6) return "below-average";
    return "poor";
  };

  // 데이터 새로고침
  const handleRefresh = () => {
    fetchQualityData();
    fetchTrendData();
  };

  // 데이터 내보내기
  const handleExport = () => {
    const csvContent = [
      [
        "키워드",
        "플랫폼",
        "카테고리",
        "NDCG 점수",
        "정확도",
        "재현율",
        "평가일자",
      ],
      ...qualityData.map((item) => [
        item.keyword,
        item.platform,
        item.category,
        item.ndcg_score,
        item.precision,
        item.recall,
        item.assessment_date,
      ]),
    ]
      .map((row) => row.join(","))
      .join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `quality_data_${
      new Date().toISOString().split("T")[0]
    }.csv`;
    link.click();
  };

  // 드로어 토글 핸들러
  const toggleDrawer = () => {
    setDrawerOpen(!drawerOpen);
  };

  if (loading) {
    return (
      <div className="p-8 bg-white min-h-[calc(100vh-52px)]">
        <div className="flex flex-col items-center justify-center min-h-[300px]">
          <Spin size="large" className="mb-4" />
          <Text className="text-gray-600">키워드 품질 데이터를 불러오는 중...</Text>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 bg-white min-h-[calc(100vh-52px)]">
        <div className="flex flex-col items-center justify-center min-h-[300px]">
          <Alert
            message="오류 발생"
            description={error}
            type="error"
            showIcon
            action={
              <Button
                type="primary"
                onClick={handleRefresh}
                icon={<ReloadOutlined />}
              >
                다시 시도
              </Button>
            }
            className="max-w-md"
          />
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 bg-white min-h-[calc(100vh-52px)]">
      {/* Breadcrumb */}
      <Breadcrumb
        className="mb-6"
        items={[
          {
            title: "검색품질 모니터링",
          },
          {
            title: "품질 대시보드",
          },
        ]}
      />

      {/* 페이지 헤더 */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <Title level={1} className="typo-heading-1 mb-2">
            Quality Dashboard
          </Title>
          <Text className="text-gray-600">
            검색 품질 모니터링 대시보드
          </Text>
        </div>
        
        <Space>
          <Button 
            icon={<FilterOutlined />}
            onClick={toggleDrawer}
          >
            필터
          </Button>
          <Button 
            icon={<DownloadOutlined />}
            onClick={handleExport}
          >
            Export CSV
          </Button>
          <Button 
            type="primary" 
            icon={<ReloadOutlined />}
            onClick={handleRefresh}
          >
            새로고침
          </Button>
        </Space>
      </div>

      {/* 메트릭 카드 섹션 */}
      <div className="mb-8">
        <Title level={3} className="typo-heading-3 mb-4">
          주요 지표
        </Title>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Card>
              <Statistic
                title="전체 키워드"
                value={summaryStats.totalKeywords}
                precision={0}
                valueStyle={{ color: '#1677ff' }}
                prefix={<DashboardOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Card>
              <Statistic
                title="평균 NDCG 점수"
                value={summaryStats.avgNdcgScore}
                precision={3}
                valueStyle={{ color: '#52c41a' }}
                prefix={<RiseOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Card>
              <Statistic
                title="평균 정확도"
                value={summaryStats.avgPrecision}
                precision={3}
                valueStyle={{ color: '#1677ff' }}
                prefix={<RiseOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Card>
              <Statistic
                title="이상치 발견"
                value={summaryStats.anomalyCount}
                precision={0}
                valueStyle={{ color: '#ff4d4f' }}
                prefix={<ExclamationCircleOutlined />}
              />
            </Card>
          </Col>
        </Row>
      </div>

      {/* 트렌드 차트 섹션 */}
      <Card className="mb-8">
        <Title level={3} className="typo-heading-3 mb-4">
          품질 트렌드
        </Title>
        {trendData && trendData.length > 0 ? (
          <TrendChart
            data={trendData}
            dateRange={filters.dateRange}
            platform={filters.platform}
          />
        ) : (
          <Empty description="트렌드 데이터가 없습니다" />
        )}
      </Card>

      {/* 키워드 테이블 섹션 */}
      <Card>
        <div className="flex justify-between items-center mb-4">
          <Title level={3} className="typo-heading-3 mb-0">
            키워드 품질 상세
          </Title>
        </div>
        <div className="mb-4">
          <Text className="text-sm text-gray-600">
            총 {summaryStats.totalKeywords}개의 키워드
          </Text>
        </div>
        <Divider className="my-4" />
        {qualityData && qualityData.length > 0 ? (
          <ComparisonTable
            data={qualityData}
            onKeywordSelect={handleKeywordSelect}
            getQualityGrade={getQualityGrade}
            filters={filters}
          />
        ) : (
          <Empty description="키워드 데이터가 없습니다" />
        )}
      </Card>

      {/* 필터 드로어 */}
      <Drawer
        title="필터 설정"
        placement="right"
        onClose={() => setDrawerOpen(false)}
        open={drawerOpen}
        width={400}
      >
        <FilterPanel 
          filters={filters}
          onFilterChange={handleFilterChange}
        />
      </Drawer>
    </div>
  );
};

export default KeywordQualityDashboard;