import React from 'react';
import { Layout } from 'antd';

const { Header } = Layout;

const GlobalHeader = () => {
  return (
    <Header className="flex items-center bg-white border-b border-gray-200 px-6 h-[52px] shadow-sm">
      <div className="flex items-center justify-between w-full h-full">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-lg font-bold text-gray-900 m-0 leading-none">
              MUSINSA SEARCH ADMIN
            </h1>
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