import React from 'react';
import { Layout } from 'antd';

const { Content } = Layout;

const GlobalContent = ({ children }) => {
  return (
    <Content className="bg-gray-50 min-h-[calc(100vh-52px)] overflow-y-auto">
      <div className="w-full h-full">
        <div className="max-w-none mx-auto h-full">
          {children}
        </div>
      </div>
    </Content>
  );
};

export default GlobalContent;