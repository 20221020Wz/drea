import React, { useEffect, useState } from 'react';
import {
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  Tag,
  Typography,
  Tooltip,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  CheckCircleOutlined,
  StopOutlined,
  CopyOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { bomApi, productApi } from '../api';
import type { BomVersion, Product, PaginatedResult } from '../types';
import dayjs from 'dayjs';

const { Title } = Typography;

const statusConfig: Record<string, { color: string; text: string }> = {
  draft: { color: 'orange', text: '草稿' },
  released: { color: 'green', text: '已发布' },
  obsolete: { color: 'red', text: '已废弃' },
};

const BomVersions: React.FC = () => {
  const navigate = useNavigate();
  const [data, setData] = useState<BomVersion[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });
  const [modalVisible, setModalVisible] = useState(false);
  const [copyModalVisible, setCopyModalVisible] = useState(false);
  const [editingItem, setEditingItem] = useState<BomVersion | null>(null);
  const [copyingItem, setCopyingItem] = useState<BomVersion | null>(null);
  const [keyword, setKeyword] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [form] = Form.useForm();
  const [copyForm] = Form.useForm();

  useEffect(() => {
    loadData();
    loadProducts();
  }, [pagination.current, pagination.pageSize]);

  const loadData = async () => {
    try {
      setLoading(true);
      const res: any = await bomApi.getVersionList({
        page: pagination.current,
        pageSize: pagination.pageSize,
        keyword,
        status: filterStatus || undefined,
      });
      if (res.success) {
        const result: PaginatedResult<BomVersion> = res.data;
        setData(result.items);
        setPagination((prev) => ({ ...prev, total: result.total }));
      }
    } catch (error: any) {
      message.error(error.message);
    } finally {
      setLoading(false);
    }
  };

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

  const handleSearch = () => {
    setPagination((prev) => ({ ...prev, current: 1 }));
    loadData();
  };

  const handleAdd = () => {
    setEditingItem(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: BomVersion) => {
    setEditingItem(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleDelete = async (id: string) => {
    try {
      const res: any = await bomApi.deleteVersion(id);
      if (res.success) {
        message.success('删除成功');
        loadData();
      }
    } catch (error: any) {
      message.error(error.message);
    }
  };

  const handleRelease = async (id: string) => {
    try {
      const res: any = await bomApi.releaseVersion(id);
      if (res.success) {
        message.success('发布成功');
        loadData();
      }
    } catch (error: any) {
      message.error(error.message);
    }
  };

  const handleObsolete = async (id: string) => {
    try {
      const res: any = await bomApi.obsoleteVersion(id);
      if (res.success) {
        message.success('已废弃');
        loadData();
      }
    } catch (error: any) {
      message.error(error.message);
    }
  };

  const handleCopy = (record: BomVersion) => {
    setCopyingItem(record);
    copyForm.resetFields();
    copyForm.setFieldsValue({ description: record.description });
    setCopyModalVisible(true);
  };

  const handleCopySubmit = async () => {
    try {
      const values = await copyForm.validateFields();
      const res: any = await bomApi.copyVersion(copyingItem!.id, values);
      if (res.success) {
        message.success('复制成功');
        setCopyModalVisible(false);
        loadData();
      }
    } catch (error: any) {
      if (error.message) {
        message.error(error.message);
      }
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingItem) {
        const res: any = await bomApi.updateVersion(editingItem.id, values);
        if (res.success) {
          message.success('更新成功');
        }
      } else {
        const res: any = await bomApi.createVersion(values);
        if (res.success) {
          message.success('创建成功');
          // 跳转到详情页编辑明细
          navigate(`/bom/${res.data.id}`);
          return;
        }
      }
      setModalVisible(false);
      loadData();
    } catch (error: any) {
      if (error.message) {
        message.error(error.message);
      }
    }
  };

  const columns = [
    {
      title: '产品编码',
      dataIndex: 'product_code',
      key: 'product_code',
      width: 120,
    },
    {
      title: '产品名称',
      dataIndex: 'product_name',
      key: 'product_name',
      width: 150,
    },
    {
      title: '版本号',
      dataIndex: 'version',
      key: 'version',
      width: 100,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const config = statusConfig[status] || { color: 'default', text: status };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '创建人',
      dataIndex: 'created_by',
      key: 'created_by',
      width: 100,
    },
    {
      title: '发布时间',
      dataIndex: 'released_at',
      key: 'released_at',
      width: 150,
      render: (text: string) => (text ? dayjs(text).format('YYYY-MM-DD HH:mm') : '-'),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (text: string) => dayjs(text).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'action',
      width: 280,
      fixed: 'right' as const,
      render: (_: any, record: BomVersion) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button type="link" icon={<EyeOutlined />} onClick={() => navigate(`/bom/${record.id}`)}>
              详情
            </Button>
          </Tooltip>
          {record.status === 'draft' && (
            <>
              <Tooltip title="编辑">
                <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
                  编辑
                </Button>
              </Tooltip>
              <Popconfirm title="确定要发布此BOM版本吗？发布后将无法修改。" onConfirm={() => handleRelease(record.id)}>
                <Button type="link" icon={<CheckCircleOutlined />} style={{ color: '#52c41a' }}>
                  发布
                </Button>
              </Popconfirm>
              <Popconfirm title="确定要删除此BOM版本吗？" onConfirm={() => handleDelete(record.id)}>
                <Button type="link" danger icon={<DeleteOutlined />}>
                  删除
                </Button>
              </Popconfirm>
            </>
          )}
          {record.status === 'released' && (
            <Popconfirm title="确定要废弃此BOM版本吗？" onConfirm={() => handleObsolete(record.id)}>
              <Button type="link" danger icon={<StopOutlined />}>
                废弃
              </Button>
            </Popconfirm>
          )}
          <Tooltip title="复制为新版本">
            <Button type="link" icon={<CopyOutlined />} onClick={() => handleCopy(record)}>
              复制
            </Button>
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Title level={3} style={{ marginBottom: '24px' }}>
        BOM版本管理
      </Title>

      <div className="table-operations">
        <div className="search-box">
          <Input
            placeholder="搜索产品编码、名称或版本号"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onPressEnter={handleSearch}
            style={{ width: 280 }}
            suffix={<SearchOutlined onClick={handleSearch} style={{ cursor: 'pointer' }} />}
          />
          <Select
            placeholder="筛选状态"
            value={filterStatus}
            onChange={(value) => {
              setFilterStatus(value);
              setPagination((prev) => ({ ...prev, current: 1 }));
            }}
            allowClear
            style={{ width: 120 }}
          >
            <Select.Option value="draft">草稿</Select.Option>
            <Select.Option value="released">已发布</Select.Option>
            <Select.Option value="obsolete">已废弃</Select.Option>
          </Select>
          <Button onClick={handleSearch}>查询</Button>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          新建BOM版本
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        loading={loading}
        scroll={{ x: 1400 }}
        pagination={{
          ...pagination,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`,
          onChange: (page, pageSize) => setPagination({ ...pagination, current: page, pageSize }),
        }}
      />

      <Modal
        title={editingItem ? '编辑BOM版本' : '新建BOM版本'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        destroyOnClose
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item
            name="product_id"
            label="产品"
            rules={[{ required: true, message: '请选择产品' }]}
          >
            <Select
              placeholder="请选择产品"
              showSearch
              optionFilterProp="children"
              disabled={!!editingItem}
            >
              {products.map((p) => (
                <Select.Option key={p.id} value={p.id}>
                  {p.code} - {p.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            name="version"
            label="版本号"
            rules={[{ required: true, message: '请输入版本号' }]}
          >
            <Input placeholder="如：V1.0、V2.0等" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="请输入版本描述" />
          </Form.Item>
          <Form.Item name="created_by" label="创建人">
            <Input placeholder="请输入创建人" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="复制BOM版本"
        open={copyModalVisible}
        onOk={handleCopySubmit}
        onCancel={() => setCopyModalVisible(false)}
        destroyOnClose
      >
        <p style={{ marginBottom: '16px', color: '#666' }}>
          将从 <strong>{copyingItem?.product_name}</strong> 的 <strong>{copyingItem?.version}</strong> 版本复制
        </p>
        <Form form={copyForm} layout="vertical" preserve={false}>
          <Form.Item
            name="new_version"
            label="新版本号"
            rules={[{ required: true, message: '请输入新版本号' }]}
          >
            <Input placeholder="如：V2.0" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="请输入版本描述" />
          </Form.Item>
          <Form.Item name="created_by" label="创建人">
            <Input placeholder="请输入创建人" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default BomVersions;
