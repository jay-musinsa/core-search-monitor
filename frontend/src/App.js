import React, { useState } from "react";
import "./styles/globals.css";
import GlobalLayout from "./components/layout/GlobalLayout";
import KeywordSearch from "./components/KeywordSearch";
import KeywordQualityDashboard from "./components/Dashboard/KeywordQualityDashboard";

function App() {
  const [activeTab, setActiveTab] = useState("search");

  return (
    <GlobalLayout activeTab={activeTab} onTabChange={setActiveTab}>
      {activeTab === "search" && <KeywordSearch />}
      {activeTab === "dashboard" && <KeywordQualityDashboard />}
    </GlobalLayout>
  );
}

export default App;
