import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Typography, Spin, message } from 'antd';
import {
  AppstoreOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { statsApi } from '../api';
import type { Stats } from '../types';

const { Title } = Typography;

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      const res: any = await statsApi.get();
      if (res.success) {
        setStats(res.data);
      }
    } catch (error: any) {
      message.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <Title level={3} style={{ marginBottom: '24px' }}>
        系统概览
      </Title>

      <Row gutter={[24, 24]}>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="产品总数"
              value={stats?.productCount || 0}
              prefix={<AppstoreOutlined style={{ color: '#1890ff' }} />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="物料总数"
              value={stats?.materialCount || 0}
              prefix={<DatabaseOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="BOM版本数"
              value={stats?.bomVersionCount || 0}
              prefix={<FileTextOutlined style={{ color: '#faad14' }} />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="已发布BOM"
              value={stats?.releasedBomCount || 0}
              prefix={<CheckCircleOutlined style={{ color: '#722ed1' }} />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      <Card style={{ marginTop: '24px' }}>
        <Title level={4}>欢迎使用BOM物料清单管理系统</Title>
        <p style={{ color: '#666', marginTop: '16px' }}>
          本系统用于管理产品的物料清单（BOM），支持以下功能：
        </p>
        <ul style={{ color: '#666', marginTop: '12px', paddingLeft: '20px' }}>
          <li>产品信息管理：添加、编辑、删除产品</li>
          <li>物料信息管理：管理所有物料的基本信息</li>
          <li>BOM版本管理：为每个产品创建多个BOM版本，支持草稿、发布、废弃状态</li>
          <li>版本对比：比较不同BOM版本之间的差异</li>
          <li>变更历史：追踪所有数据的变更记录</li>
        </ul>
      </Card>
    </div>
  );
};

export default Dashboard;
