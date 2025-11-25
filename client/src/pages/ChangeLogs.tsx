import React, { useEffect, useState } from 'react';
import { Table, Select, Typography, Tag, Card, Space, message, Tooltip } from 'antd';
import { changeLogApi } from '../api';
import type { ChangeLog, PaginatedResult } from '../types';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

const entityTypeConfig: Record<string, { text: string; color: string }> = {
  product: { text: '产品', color: 'blue' },
  material: { text: '物料', color: 'green' },
  bom_version: { text: 'BOM版本', color: 'orange' },
  bom_item: { text: 'BOM明细', color: 'purple' },
};

const actionConfig: Record<string, { text: string; color: string }> = {
  create: { text: '创建', color: 'green' },
  update: { text: '更新', color: 'blue' },
  delete: { text: '删除', color: 'red' },
  release: { text: '发布', color: 'cyan' },
  obsolete: { text: '废弃', color: 'magenta' },
};

const ChangeLogs: React.FC = () => {
  const [data, setData] = useState<ChangeLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });
  const [entityType, setEntityType] = useState<string>('');

  useEffect(() => {
    loadData();
  }, [pagination.current, pagination.pageSize, entityType]);

  const loadData = async () => {
    try {
      setLoading(true);
      const res: any = await changeLogApi.getList({
        page: pagination.current,
        pageSize: pagination.pageSize,
        entity_type: entityType || undefined,
      });
      if (res.success) {
        const result: PaginatedResult<ChangeLog> = res.data;
        setData(result.items);
        setPagination((prev) => ({ ...prev, total: result.total }));
      }
    } catch (error: any) {
      message.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  const renderChangeDetail = (record: ChangeLog) => {
    const oldVal = record.old_value_parsed;
    const newVal = record.new_value_parsed;

    if (record.action === 'create' && newVal) {
      return (
        <div style={{ fontSize: '12px', color: '#666' }}>
          {newVal.code && <div>编码: {newVal.code}</div>}
          {newVal.name && <div>名称: {newVal.name}</div>}
          {newVal.version && <div>版本: {newVal.version}</div>}
        </div>
      );
    }

    if (record.action === 'delete' && oldVal) {
      return (
        <div style={{ fontSize: '12px', color: '#666' }}>
          {oldVal.code && <div>编码: {oldVal.code}</div>}
          {oldVal.name && <div>名称: {oldVal.name}</div>}
          {oldVal.version && <div>版本: {oldVal.version}</div>}
        </div>
      );
    }

    if (record.action === 'update' && oldVal && newVal) {
      const changes: string[] = [];
      const keys = new Set([...Object.keys(oldVal), ...Object.keys(newVal)]);
      keys.forEach((key) => {
        if (
          key !== 'updated_at' &&
          key !== 'created_at' &&
          JSON.stringify(oldVal[key]) !== JSON.stringify(newVal[key])
        ) {
          changes.push(`${key}: ${oldVal[key] || '空'} → ${newVal[key] || '空'}`);
        }
      });
      return (
        <div style={{ fontSize: '12px', color: '#666' }}>
          {changes.slice(0, 3).map((c, i) => (
            <div key={i}>{c}</div>
          ))}
          {changes.length > 3 && <div>...等{changes.length}处变更</div>}
        </div>
      );
    }

    if (record.action === 'release' || record.action === 'obsolete') {
      return (
        <div style={{ fontSize: '12px', color: '#666' }}>
          {newVal?.version && <div>版本: {newVal.version}</div>}
          {newVal?.product_name && <div>产品: {newVal.product_name}</div>}
        </div>
      );
    }

    return '-';
  };

  const columns = [
    {
      title: '时间',
      dataIndex: 'changed_at',
      key: 'changed_at',
      width: 180,
      render: (text: string) => dayjs(text).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '类型',
      dataIndex: 'entity_type',
      key: 'entity_type',
      width: 100,
      render: (type: string) => {
        const config = entityTypeConfig[type] || { text: type, color: 'default' };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      width: 80,
      render: (action: string) => {
        const config = actionConfig[action] || { text: action, color: 'default' };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '变更详情',
      key: 'detail',
      render: (_: any, record: ChangeLog) => renderChangeDetail(record),
    },
    {
      title: '操作人',
      dataIndex: 'changed_by',
      key: 'changed_by',
      width: 100,
      render: (text: string) => text || '-',
    },
    {
      title: '实体ID',
      dataIndex: 'entity_id',
      key: 'entity_id',
      width: 150,
      render: (text: string) => (
        <Tooltip title={text}>
          <Text copyable style={{ fontSize: '12px' }}>
            {text.substring(0, 8)}...
          </Text>
        </Tooltip>
      ),
    },
  ];

  return (
    <div>
      <Title level={3} style={{ marginBottom: '24px' }}>
        变更历史
      </Title>

      <Card>
        <Space style={{ marginBottom: '16px' }}>
          <Text>筛选类型:</Text>
          <Select
            placeholder="全部类型"
            value={entityType}
            onChange={(value) => {
              setEntityType(value);
              setPagination((prev) => ({ ...prev, current: 1 }));
            }}
            allowClear
            style={{ width: 150 }}
          >
            <Select.Option value="product">产品</Select.Option>
            <Select.Option value="material">物料</Select.Option>
            <Select.Option value="bom_version">BOM版本</Select.Option>
          </Select>
        </Space>

        <Table
          columns={columns}
          dataSource={data}
          rowKey="id"
          loading={loading}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (page, pageSize) => setPagination({ ...pagination, current: page, pageSize }),
          }}
        />
      </Card>
    </div>
  );
};

export default ChangeLogs;
