import React, { useEffect, useState } from 'react';
import {
  Card,
  Select,
  Button,
  Table,
  Typography,
  Space,
  message,
  Empty,
  Tag,
  Divider,
} from 'antd';
import { SwapOutlined } from '@ant-design/icons';
import { bomApi, productApi } from '../api';
import type { Product, BomVersion, VersionCompareResult, BomItem } from '../types';

const { Title, Text } = Typography;

const BomCompare: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [productId, setProductId] = useState<string>('');
  const [versions, setVersions] = useState<BomVersion[]>([]);
  const [version1, setVersion1] = useState<string>('');
  const [version2, setVersion2] = useState<string>('');
  const [compareResult, setCompareResult] = useState<VersionCompareResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadProducts();
  }, []);

  useEffect(() => {
    if (productId) {
      loadProductVersions();
      setVersion1('');
      setVersion2('');
      setCompareResult(null);
    }
  }, [productId]);

  const loadProducts = async () => {
    try {
      const res: any = await productApi.getAll();
      if (res.success) {
        setProducts(res.data);
      }
    } catch (error: any) {
      message.error(error.message);
    }
  };

  const loadProductVersions = async () => {
    try {
      const res: any = await bomApi.getProductVersions(productId);
      if (res.success) {
        setVersions(res.data);
      }
    } catch (error: any) {
      message.error(error.message);
    }
  };

  const handleCompare = async () => {
    if (!version1 || !version2) {
      message.warning('请选择要对比的两个版本');
      return;
    }
    if (version1 === version2) {
      message.warning('请选择不同的版本进行对比');
      return;
    }

    try {
      setLoading(true);
      const res: any = await bomApi.compareVersions(version1, version2);
      if (res.success) {
        setCompareResult(res.data);
      }
    } catch (error: any) {
      message.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSwap = () => {
    const temp = version1;
    setVersion1(version2);
    setVersion2(temp);
    setCompareResult(null);
  };

  const getVersionLabel = (versionId: string) => {
    const v = versions.find((v) => v.id === versionId);
    return v ? v.version : '';
  };

  const itemColumns = [
    {
      title: '物料编码',
      dataIndex: 'material_code',
      key: 'material_code',
      width: 120,
    },
    {
      title: '物料名称',
      dataIndex: 'material_name',
      key: 'material_name',
      width: 150,
    },
    {
      title: '规格型号',
      dataIndex: 'material_specification',
      key: 'material_specification',
      width: 150,
    },
    {
      title: '用量',
      dataIndex: 'quantity',
      key: 'quantity',
      width: 80,
    },
    {
      title: '单位',
      dataIndex: 'unit',
      key: 'unit',
      width: 60,
    },
    {
      title: '位号',
      dataIndex: 'position',
      key: 'position',
      width: 100,
    },
  ];

  const modifiedColumns = [
    {
      title: '物料编码',
      dataIndex: ['item', 'material_code'],
      key: 'material_code',
      width: 120,
    },
    {
      title: '物料名称',
      dataIndex: ['item', 'material_name'],
      key: 'material_name',
      width: 150,
    },
    {
      title: '变更内容',
      key: 'changes',
      render: (_: any, record: { item: BomItem; oldItem: BomItem; changes: string[] }) => (
        <div>
          {record.changes.map((change, index) => (
            <div key={index} style={{ color: '#faad14' }}>
              {change}
            </div>
          ))}
        </div>
      ),
    },
  ];

  return (
    <div>
      <Title level={3} style={{ marginBottom: '24px' }}>
        BOM版本对比
      </Title>

      <Card>
        <Space wrap size="large" style={{ marginBottom: '24px' }}>
          <div>
            <Text strong style={{ marginRight: '8px' }}>选择产品:</Text>
            <Select
              placeholder="请选择产品"
              value={productId}
              onChange={setProductId}
              style={{ width: 250 }}
              showSearch
              optionFilterProp="children"
            >
              {products.map((p) => (
                <Select.Option key={p.id} value={p.id}>
                  {p.code} - {p.name}
                </Select.Option>
              ))}
            </Select>
          </div>
          {productId && (
            <>
              <div>
                <Text strong style={{ marginRight: '8px' }}>版本1:</Text>
                <Select
                  placeholder="选择版本"
                  value={version1}
                  onChange={(v) => {
                    setVersion1(v);
                    setCompareResult(null);
                  }}
                  style={{ width: 150 }}
                >
                  {versions.map((v) => (
                    <Select.Option key={v.id} value={v.id}>
                      {v.version}
                    </Select.Option>
                  ))}
                </Select>
              </div>
              <Button icon={<SwapOutlined />} onClick={handleSwap} disabled={!version1 || !version2}>
                交换
              </Button>
              <div>
                <Text strong style={{ marginRight: '8px' }}>版本2:</Text>
                <Select
                  placeholder="选择版本"
                  value={version2}
                  onChange={(v) => {
                    setVersion2(v);
                    setCompareResult(null);
                  }}
                  style={{ width: 150 }}
                >
                  {versions.map((v) => (
                    <Select.Option key={v.id} value={v.id}>
                      {v.version}
                    </Select.Option>
                  ))}
                </Select>
              </div>
              <Button type="primary" onClick={handleCompare} loading={loading}>
                对比
              </Button>
            </>
          )}
        </Space>

        {!productId && (
          <Empty description="请先选择产品" />
        )}

        {productId && versions.length === 0 && (
          <Empty description="该产品暂无BOM版本" />
        )}

        {productId && versions.length > 0 && !compareResult && (
          <Empty description="请选择两个版本进行对比" />
        )}

        {compareResult && (
          <div>
            <Divider />
            <div style={{ marginBottom: '16px' }}>
              <Text>
                对比结果: <Tag>{getVersionLabel(version1)}</Tag> vs <Tag>{getVersionLabel(version2)}</Tag>
              </Text>
            </div>

            {compareResult.added.length === 0 &&
              compareResult.removed.length === 0 &&
              compareResult.modified.length === 0 && (
                <Empty description="两个版本完全相同" />
              )}

            {compareResult.added.length > 0 && (
              <div className="version-compare-section">
                <h4>
                  <Tag color="green">新增</Tag> {getVersionLabel(version2)} 相比 {getVersionLabel(version1)} 新增的物料 ({compareResult.added.length})
                </h4>
                <Table
                  columns={itemColumns}
                  dataSource={compareResult.added}
                  rowKey="id"
                  pagination={false}
                  size="small"
                  rowClassName="compare-added"
                />
              </div>
            )}

            {compareResult.removed.length > 0 && (
              <div className="version-compare-section">
                <h4>
                  <Tag color="red">删除</Tag> {getVersionLabel(version2)} 相比 {getVersionLabel(version1)} 删除的物料 ({compareResult.removed.length})
                </h4>
                <Table
                  columns={itemColumns}
                  dataSource={compareResult.removed}
                  rowKey="id"
                  pagination={false}
                  size="small"
                  rowClassName="compare-removed"
                />
              </div>
            )}

            {compareResult.modified.length > 0 && (
              <div className="version-compare-section">
                <h4>
                  <Tag color="orange">修改</Tag> {getVersionLabel(version2)} 相比 {getVersionLabel(version1)} 修改的物料 ({compareResult.modified.length})
                </h4>
                <Table
                  columns={modifiedColumns}
                  dataSource={compareResult.modified}
                  rowKey={(record) => record.item.id}
                  pagination={false}
                  size="small"
                  rowClassName="compare-modified"
                />
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
};

export default BomCompare;
