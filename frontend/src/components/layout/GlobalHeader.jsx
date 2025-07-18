import React from 'react';
import { Layout } from 'antd';

const { Header } = Layout;

const GlobalHeader = () => {
  return (
    <Header className="flex items-center bg-white border-b border-gray-300 px-6 h-[52px]">
      <div className="flex items-center justify-start w-full h-full">
        <h1 className="text-xl font-bold text-gray-900 m-0 leading-none">
          MUSINSA Search ADMIN
        </h1>
      </div>
    </Header>
  );
};

export default GlobalHeader;