import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from 'antd';
import AppSider from './components/AppSider';
import Dashboard from './pages/Dashboard';
import Products from './pages/Products';
import Materials from './pages/Materials';
import BomVersions from './pages/BomVersions';
import BomDetail from './pages/BomDetail';
import BomCompare from './pages/BomCompare';
import ChangeLogs from './pages/ChangeLogs';

const { Content } = Layout;

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Layout style={{ minHeight: '100vh' }}>
        <AppSider />
        <Layout style={{ marginLeft: 220 }}>
          <Content style={{ margin: '24px', background: '#fff', padding: '24px', borderRadius: '8px', minHeight: 'calc(100vh - 48px)' }}>
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/products" element={<Products />} />
              <Route path="/materials" element={<Materials />} />
              <Route path="/bom" element={<BomVersions />} />
              <Route path="/bom/:id" element={<BomDetail />} />
              <Route path="/bom/compare" element={<BomCompare />} />
              <Route path="/change-logs" element={<ChangeLogs />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </BrowserRouter>
  );
};

export default App;
