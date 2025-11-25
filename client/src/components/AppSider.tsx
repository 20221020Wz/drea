import React from 'react';
import { Layout, Menu } from 'antd';
import {
  DashboardOutlined,
  AppstoreOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  HistoryOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';

const { Sider } = Layout;

const AppSider: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: '仪表盘',
    },
    {
      key: '/products',
      icon: <AppstoreOutlined />,
      label: '产品管理',
    },
    {
      key: '/materials',
      icon: <DatabaseOutlined />,
      label: '物料管理',
    },
    {
      key: '/bom',
      icon: <FileTextOutlined />,
      label: 'BOM版本',
    },
    {
      key: '/bom/compare',
      icon: <SwapOutlined />,
      label: '版本对比',
    },
    {
      key: '/change-logs',
      icon: <HistoryOutlined />,
      label: '变更历史',
    },
  ];

  return (
    <Sider
      theme="dark"
      width={220}
      style={{
        overflow: 'auto',
        height: '100vh',
        position: 'fixed',
        left: 0,
        top: 0,
        bottom: 0,
      }}
    >
      <div className="logo" style={{ padding: '16px 24px', borderBottom: '1px solid #303030' }}>
        <FileTextOutlined style={{ fontSize: '24px' }} />
        <span>BOM管理系统</span>
      </div>
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={({ key }) => navigate(key)}
        style={{ borderRight: 0, marginTop: '8px' }}
      />
    </Sider>
  );
};

export default AppSider;
