import React, { useState, useEffect } from "react";
import { Select, Slider, Typography, Space, Divider, Row, Col } from "antd";

const { Text, Title } = Typography;
const { Option } = Select;

const FilterPanel = ({
  filters,
  onFilterChange,
  collapsed = false,
  inline = false,
}) => {
  const [localFilters, setLocalFilters] = useState(filters);

  // 필터 옵션 정의
  const filterOptions = {
    platform: [
      { value: "all", label: "모든 플랫폼" },
      { value: "musinsa", label: "무신사" },
      { value: "29cm", label: "29CM" },
    ],
    category: [
      { value: "all", label: "모든 카테고리" },
      { value: "clothing", label: "의류" },
      { value: "shoes", label: "신발" },
      { value: "bags", label: "가방" },
      { value: "accessories", label: "액세서리" },
    ],
    dateRange: [
      { value: "1d", label: "1일" },
      { value: "7d", label: "7일" },
      { value: "30d", label: "30일" },
      { value: "90d", label: "90일" },
    ],
  };

  // 로컬 필터 업데이트
  useEffect(() => {
    setLocalFilters(filters);
  }, [filters]);

  // 필터 변경 핸들러
  const handleFilterChange = (key, value) => {
    const newFilters = { ...localFilters, [key]: value };
    setLocalFilters(newFilters);
    onFilterChange(newFilters);
  };

  // 품질 임계값 변경 핸들러
  const handleThresholdChange = (value) => {
    const newFilters = { ...localFilters, threshold: parseFloat(value) };
    setLocalFilters(newFilters);
    onFilterChange(newFilters);
  };

  if (collapsed) {
    return null;
  }

  // 인라인 모드 렌더링
  if (inline) {
    return (
      <div>
        <Title level={5} className="mb-4">
          필터
        </Title>

        <Row gutter={[16, 16]} align="middle">
          {/* 플랫폼 필터 */}
          <Col xs={24} sm={12} md={6}>
            <div>
              <Text strong className="block mb-2">
                플랫폼
              </Text>
              <Select
                value={localFilters.platform}
                onChange={(value) => handleFilterChange("platform", value)}
                className="w-full"
                placeholder="플랫폼 선택"
              >
                {filterOptions.platform.map((option) => (
                  <Option key={option.value} value={option.value}>
                    {option.label}
                  </Option>
                ))}
              </Select>
            </div>
          </Col>

          {/* 카테고리 필터 */}
          <Col xs={24} sm={12} md={6}>
            <div>
              <Text strong className="block mb-2">
                카테고리
              </Text>
              <Select
                value={localFilters.category}
                onChange={(value) => handleFilterChange("category", value)}
                className="w-full"
                placeholder="카테고리 선택"
              >
                {filterOptions.category.map((option) => (
                  <Option key={option.value} value={option.value}>
                    {option.label}
                  </Option>
                ))}
              </Select>
            </div>
          </Col>

          {/* 날짜 범위 필터 */}
          <Col xs={24} sm={12} md={6}>
            <div>
              <Text strong className="block mb-2">
                날짜 범위
              </Text>
              <Select
                value={localFilters.dateRange}
                onChange={(value) => handleFilterChange("dateRange", value)}
                className="w-full"
                placeholder="전체 기간"
                allowClear
              >
                {filterOptions.dateRange.map((option) => (
                  <Option key={option.value} value={option.value}>
                    {option.label}
                  </Option>
                ))}
              </Select>
            </div>
          </Col>

          {/* 품질 임계값 */}
          <Col xs={24} sm={12} md={6}>
            <div>
              <Text strong className="block mb-2">
                품질 임계값
              </Text>
              <div>
                <Slider
                  min={0}
                  max={1}
                  step={0.1}
                  value={localFilters.threshold || 0}
                  onChange={(value) => handleThresholdChange(value)}
                  tooltip={{ formatter: (value) => `${value}` }}
                  marks={{
                    0: "0",
                    0.5: "0.5",
                    1: "1",
                  }}
                />
                <div className="text-center mt-1">
                  <Text className="text-xs text-gray-500">
                    {localFilters.threshold || 0} (0: 모든 데이터)
                  </Text>
                </div>
              </div>
            </div>
          </Col>
        </Row>
      </div>
    );
  }

  // 기존 세로 모드 렌더링
  return (
    <div className="p-6">
      <Title level={4} className="mb-6">
        필터
      </Title>

      <Space direction="vertical" className="w-full" size="large">
        {/* 플랫폼 필터 */}
        <div>
          <Text strong className="block mb-2">
            플랫폼
          </Text>
          <Select
            value={localFilters.platform}
            onChange={(value) => handleFilterChange("platform", value)}
            className="w-full"
            placeholder="플랫폼을 선택하세요"
          >
            {filterOptions.platform.map((option) => (
              <Option key={option.value} value={option.value}>
                {option.label}
              </Option>
            ))}
          </Select>
        </div>

        <Divider />

        {/* 카테고리 필터 */}
        <div>
          <Text strong className="block mb-2">
            카테고리
          </Text>
          <Select
            value={localFilters.category}
            onChange={(value) => handleFilterChange("category", value)}
            className="w-full"
            placeholder="카테고리를 선택하세요"
          >
            {filterOptions.category.map((option) => (
              <Option key={option.value} value={option.value}>
                {option.label}
              </Option>
            ))}
          </Select>
        </div>

        <Divider />

        {/* 날짜 범위 필터 */}
        <div>
          <Text strong className="block mb-2">
            날짜 범위
          </Text>
          <Select
            value={localFilters.dateRange}
            onChange={(value) => handleFilterChange("dateRange", value)}
            className="w-full"
            placeholder="날짜 범위를 선택하세요 (선택안함: 전체)"
            allowClear
          >
            {filterOptions.dateRange.map((option) => (
              <Option key={option.value} value={option.value}>
                {option.label}
              </Option>
            ))}
          </Select>
        </div>

        <Divider />

        {/* 품질 임계값 */}
        <div>
          <Text strong className="block mb-2">
            품질 임계값
          </Text>
          <div className="px-2">
            <Slider
              min={0}
              max={1}
              step={0.1}
              value={localFilters.threshold || 0}
              onChange={(value) => handleThresholdChange(value)}
              tooltip={{ formatter: (value) => `${value}` }}
              marks={{
                0: "0",
                0.5: "0.5",
                1: "1",
              }}
            />
            <div className="text-center mt-2">
              <Text className="text-sm text-gray-600">
                현재 값: {localFilters.threshold || 0} (0: 모든 데이터 표시)
              </Text>
            </div>
          </div>
        </div>
      </Space>
    </div>
  );
};

export default FilterPanel;
