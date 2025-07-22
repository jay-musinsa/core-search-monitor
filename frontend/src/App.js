import React, { useState, useEffect } from "react";
import "./styles/globals.css";
import GlobalLayout from "./components/layout/GlobalLayout";
import KeywordSearch from "./components/KeywordSearch";
import KeywordQualityDashboard from "./components/Dashboard/KeywordQualityDashboard";
import EvaluatorConfigModal from "./components/EvaluatorConfigModal";
import ErrorBoundary from "./components/ErrorBoundary";
import { message } from "antd";
import { BACKEND_URL } from "./config";

function App() {
  const [activeTab, setActiveTab] = useState("search");

  // 평가기 설정 관련 상태
  const [showEvaluatorConfig, setShowEvaluatorConfig] = useState(false);
  const [evaluatorConfigs, setEvaluatorConfigs] = useState({});

  // 평가기 설정 로드
  const loadEvaluatorConfigs = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/evaluator-config`);
      const data = await response.json();
      if (data.success) {
        setEvaluatorConfigs(data.configs);
      }
    } catch (error) {
      console.error("평가기 설정 로드 실패:", error);
    }
  };

  // 평가기 설정 저장
  const saveEvaluatorConfigs = async (configs) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/evaluator-config`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ configs }),
      });
      const data = await response.json();
      if (data.success) {
        setEvaluatorConfigs(configs);
        message.success("평가기 설정이 저장되었습니다.");
      } else {
        message.error("설정 저장 실패: " + data.error);
      }
    } catch (error) {
      console.error("평가기 설정 저장 실패:", error);
      message.error("설정 저장 중 오류가 발생했습니다.");
    }
  };

  // 컴포넌트 마운트 시 평가기 설정 로드
  useEffect(() => {
    loadEvaluatorConfigs();
  }, []);

  return (
    <ErrorBoundary>
      <GlobalLayout activeTab={activeTab} onTabChange={setActiveTab}>
        {activeTab === "search" && (
          <KeywordSearch
            showEvaluatorConfig={showEvaluatorConfig}
            setShowEvaluatorConfig={setShowEvaluatorConfig}
          />
        )}
        {activeTab === "dashboard" && <KeywordQualityDashboard />}

        {/* 평가기 설정 모달 */}
        <EvaluatorConfigModal
          visible={showEvaluatorConfig}
          configs={evaluatorConfigs}
          onSave={saveEvaluatorConfigs}
          onCancel={() => setShowEvaluatorConfig(false)}
        />
      </GlobalLayout>
    </ErrorBoundary>
  );
}

export default App;
