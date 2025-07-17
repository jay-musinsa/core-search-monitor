import React, { useState, useEffect } from "react";
import "./FilterPanel.css";

const FilterPanel = ({ filters, onFilterChange, collapsed = false }) => {
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

  return (
    <div className="filter-panel">
      <div className="filter-header">
        <h3>필터</h3>
      </div>

      <div className="filter-sections">
        {/* 플랫폼 필터 */}
        <div className="filter-section">
          <label className="filter-label">플랫폼</label>
          <select
            value={localFilters.platform}
            onChange={(e) => handleFilterChange("platform", e.target.value)}
            className="filter-select"
          >
            {filterOptions.platform.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* 카테고리 필터 */}
        <div className="filter-section">
          <label className="filter-label">카테고리</label>
          <select
            value={localFilters.category}
            onChange={(e) => handleFilterChange("category", e.target.value)}
            className="filter-select"
          >
            {filterOptions.category.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* 날짜 범위 필터 */}
        <div className="filter-section">
          <label className="filter-label">날짜 범위</label>
          <select
            value={localFilters.dateRange}
            onChange={(e) => handleFilterChange("dateRange", e.target.value)}
            className="filter-select"
          >
            {filterOptions.dateRange.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* 품질 임계값 */}
        <div className="filter-section">
          <label className="filter-label">품질 임계값</label>
          <div className="threshold-input">
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={localFilters.threshold}
              onChange={(e) => handleThresholdChange(e.target.value)}
              className="threshold-slider"
            />
            <span className="threshold-value">{localFilters.threshold}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FilterPanel;
