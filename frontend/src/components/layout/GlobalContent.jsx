import React from 'react';
import { Layout } from 'antd';

const { Content } = Layout;

const GlobalContent = ({ children }) => {
  return (
    <Content className="bg-white min-h-[calc(100vh-52px)] overflow-y-auto">
      <div className="min-w-[1326px] h-full">
        {children}
      </div>
    </Content>
  );
};

export default GlobalContent;