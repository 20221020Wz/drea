import React, { useEffect, useState } from 'react';
import {
  Card,
  Descriptions,
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  message,
  Popconfirm,
  Tag,
  Typography,
  Spin,
} from 'antd';
import {
  ArrowLeftOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { bomApi, materialApi, changeLogApi } from '../api';
import type { BomVersion, BomItem, Material, ChangeLog } from '../types';
import dayjs from 'dayjs';

const { Title } = Typography;

const statusConfig: Record<string, { color: string; text: string }> = {
  draft: { color: 'orange', text: '草稿' },
  released: { color: 'green', text: '已发布' },
  obsolete: { color: 'red', text: '已废弃' },
};

const BomDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [version, setVersion] = useState<BomVersion | null>(null);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [changeLogs, setChangeLogs] = useState<ChangeLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingItem, setEditingItem] = useState<BomItem | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    if (id) {
      loadData();
      loadMaterials();
      loadChangeLogs();
    }
  }, [id]);

  const loadData = async () => {
    try {
      setLoading(true);
      const res: any = await bomApi.getVersionById(id!);
      if (res.success) {
        setVersion(res.data);
      }
    } catch (error: any) {
      message.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  const loadMaterials = async () => {
    try {
      const res: any = await materialApi.getAll();
      if (res.success) {
        setMaterials(res.data);
      }
    } catch (error: any) {
      message.error(error.message);
    }
  };

  const loadChangeLogs = async () => {
    try {
      const res: any = await changeLogApi.getEntityLogs('bom_version', id!);
      if (res.success) {
        setChangeLogs(res.data);
      }
    } catch (error: any) {
      // 忽略错误
    }
  };

  const handleAddItem = () => {
    setEditingItem(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEditItem = (record: BomItem) => {
    setEditingItem(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleDeleteItem = async (itemId: string) => {
    if (!version) return;

    const newItems = version.items?.filter((item) => item.id !== itemId) || [];
    try {
      const res: any = await bomApi.updateVersion(version.id, { items: newItems });
      if (res.success) {
        message.success('删除成功');
        loadData();
      }
    } catch (error: any) {
      message.error(error.message);
    }
  };

  const handleSubmitItem = async () => {
    if (!version) return;

    try {
      const values = await form.validateFields();
      let newItems: BomItem[];

      if (editingItem) {
        newItems =
          version.items?.map((item) =>
            item.id === editingItem.id ? { ...item, ...values } : item
          ) || [];
      } else {
        newItems = [...(version.items || []), { ...values, id: `temp_${Date.now()}` }];
      }

      const res: any = await bomApi.updateVersion(version.id, { items: newItems });
      if (res.success) {
        message.success(editingItem ? '更新成功' : '添加成功');
        setModalVisible(false);
        loadData();
      }
    } catch (error: any) {
      if (error.message) {
        message.error(error.message);
      }
    }
  };

  const handleRelease = async () => {
    try {
      const res: any = await bomApi.releaseVersion(version!.id);
      if (res.success) {
        message.success('发布成功');
        loadData();
      }
    } catch (error: any) {
      message.error(error.message);
    }
  };

  const calculateTotalCost = () => {
    if (!version?.items) return 0;
    return version.items.reduce((sum, item) => {
      return sum + (item.material_price || 0) * item.quantity;
    }, 0);
  };

  const columns = [
    {
      title: '序号',
      key: 'index',
      width: 60,
      render: (_: any, __: any, index: number) => index + 1,
    },
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
      title: '单价',
      dataIndex: 'material_price',
      key: 'material_price',
      width: 100,
      render: (price: number) => (price ? `¥${price.toFixed(2)}` : '-'),
    },
    {
      title: '金额',
      key: 'amount',
      width: 100,
      render: (_: any, record: BomItem) =>
        record.material_price
          ? `¥${(record.material_price * record.quantity).toFixed(2)}`
          : '-',
    },
    {
      title: '位号',
      dataIndex: 'position',
      key: 'position',
      width: 100,
    },
    {
      title: '备注',
      dataIndex: 'remark',
      key: 'remark',
      ellipsis: true,
    },
    ...(version?.status === 'draft'
      ? [
          {
            title: '操作',
            key: 'action',
            width: 150,
            render: (_: any, record: BomItem) => (
              <Space>
                <Button type="link" icon={<EditOutlined />} onClick={() => handleEditItem(record)}>
                  编辑
                </Button>
                <Popconfirm
                  title="确定要删除此物料吗？"
                  onConfirm={() => handleDeleteItem(record.id)}
                >
                  <Button type="link" danger icon={<DeleteOutlined />}>
                    删除
                  </Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]
      : []),
  ];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!version) {
    return <div>BOM版本不存在</div>;
  }

  const statusCfg = statusConfig[version.status] || { color: 'default', text: version.status };

  return (
    <div>
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/bom')}>
            返回
          </Button>
          <Title level={3} style={{ margin: 0 }}>
            BOM详情
          </Title>
        </Space>
        {version.status === 'draft' && (
          <Popconfirm title="确定要发布此BOM版本吗？发布后将无法修改。" onConfirm={handleRelease}>
            <Button type="primary" icon={<CheckCircleOutlined />}>
              发布版本
            </Button>
          </Popconfirm>
        )}
      </div>

      <Card style={{ marginBottom: '24px' }}>
        <Descriptions title="基本信息" bordered column={3}>
          <Descriptions.Item label="产品编码">{version.product_code}</Descriptions.Item>
          <Descriptions.Item label="产品名称">{version.product_name}</Descriptions.Item>
          <Descriptions.Item label="版本号">{version.version}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={statusCfg.color}>{statusCfg.text}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="创建人">{version.created_by || '-'}</Descriptions.Item>
          <Descriptions.Item label="发布时间">
            {version.released_at ? dayjs(version.released_at).format('YYYY-MM-DD HH:mm') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="描述" span={3}>
            {version.description || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {dayjs(version.created_at).format('YYYY-MM-DD HH:mm')}
          </Descriptions.Item>
          <Descriptions.Item label="更新时间">
            {dayjs(version.updated_at).format('YYYY-MM-DD HH:mm')}
          </Descriptions.Item>
          <Descriptions.Item label="预估成本">
            <strong style={{ color: '#1890ff' }}>¥{calculateTotalCost().toFixed(2)}</strong>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card
        title="物料清单"
        extra={
          version.status === 'draft' && (
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAddItem}>
              添加物料
            </Button>
          )
        }
      >
        <Table
          columns={columns}
          dataSource={version.items || []}
          rowKey="id"
          pagination={false}
          scroll={{ x: 1200 }}
          summary={() => (
            <Table.Summary fixed>
              <Table.Summary.Row>
                <Table.Summary.Cell index={0} colSpan={7}>
                  <strong>合计</strong>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={1}>
                  <strong style={{ color: '#1890ff' }}>¥{calculateTotalCost().toFixed(2)}</strong>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={2} colSpan={version.status === 'draft' ? 3 : 2} />
              </Table.Summary.Row>
            </Table.Summary>
          )}
        />
      </Card>

      {changeLogs.length > 0 && (
        <Card title="变更记录" style={{ marginTop: '24px' }}>
          <div style={{ maxHeight: '300px', overflow: 'auto' }}>
            {changeLogs.map((log) => (
              <div key={log.id} className="change-log-item">
                <span className="change-log-time">
                  {dayjs(log.changed_at).format('YYYY-MM-DD HH:mm:ss')}
                </span>
                <span className="change-log-action">
                  {log.action === 'create' && '创建'}
                  {log.action === 'update' && '更新'}
                  {log.action === 'release' && '发布'}
                  {log.action === 'obsolete' && '废弃'}
                </span>
                {log.changed_by && <span> - 操作人: {log.changed_by}</span>}
              </div>
            ))}
          </div>
        </Card>
      )}

      <Modal
        title={editingItem ? '编辑物料' : '添加物料'}
        open={modalVisible}
        onOk={handleSubmitItem}
        onCancel={() => setModalVisible(false)}
        destroyOnClose
        width={600}
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item
            name="material_id"
            label="物料"
            rules={[{ required: true, message: '请选择物料' }]}
          >
            <Select
              placeholder="请选择物料"
              showSearch
              optionFilterProp="children"
              onChange={(value) => {
                const material = materials.find((m) => m.id === value);
                if (material) {
                  form.setFieldsValue({ unit: material.unit });
                }
              }}
            >
              {materials.map((m) => (
                <Select.Option key={m.id} value={m.id}>
                  {m.code} - {m.name} {m.specification ? `(${m.specification})` : ''}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            name="quantity"
            label="用量"
            rules={[{ required: true, message: '请输入用量' }]}
          >
            <InputNumber min={0.001} precision={3} style={{ width: '100%' }} placeholder="请输入用量" />
          </Form.Item>
          <Form.Item
            name="unit"
            label="单位"
            rules={[{ required: true, message: '请输入单位' }]}
          >
            <Input placeholder="单位" />
          </Form.Item>
          <Form.Item name="position" label="位号">
            <Input placeholder="如：C1, R1等" />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} placeholder="请输入备注" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default BomDetail;
