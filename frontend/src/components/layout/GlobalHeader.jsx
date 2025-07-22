import React from 'react';
import { Layout } from 'antd';

const { Header } = Layout;

const GlobalHeader = () => {
  return (
    <Header className="flex items-center bg-white border-b border-gray-200 px-6 h-[52px] shadow-sm">
      <div className="flex items-center justify-between w-full h-full">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-blue-600 rounded-lg flex items-center justify-center shadow-sm">
            <span className="text-white font-bold text-sm">M</span>
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900 m-0 leading-none">
              MUSINSA Search Monitor
            </h1>
            <div className="text-xs text-gray-500 font-medium">Admin Dashboard</div>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
          <span className="text-xs text-gray-600 font-medium">실시간 연결</span>
        </div>
      </div>
    </Header>
  );
};

export default GlobalHeader;