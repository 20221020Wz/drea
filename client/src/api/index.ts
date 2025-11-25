import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
});

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.error || error.message || '请求失败';
    return Promise.reject(new Error(message));
  }
);

// 产品API
export const productApi = {
  getList: (params?: any) => api.get('/products', { params }),
  getAll: () => api.get('/products/all/list'),
  getById: (id: string) => api.get(`/products/${id}`),
  create: (data: any) => api.post('/products', data),
  update: (id: string, data: any) => api.put(`/products/${id}`, data),
  delete: (id: string) => api.delete(`/products/${id}`),
};

// 物料API
export const materialApi = {
  getList: (params?: any) => api.get('/materials', { params }),
  getAll: () => api.get('/materials/all/list'),
  getById: (id: string) => api.get(`/materials/${id}`),
  create: (data: any) => api.post('/materials', data),
  update: (id: string, data: any) => api.put(`/materials/${id}`, data),
  delete: (id: string) => api.delete(`/materials/${id}`),
  getCategories: () => api.get('/materials/categories/list'),
};

// BOM API
export const bomApi = {
  getVersionList: (params?: any) => api.get('/bom/versions', { params }),
  getVersionById: (id: string) => api.get(`/bom/versions/${id}`),
  createVersion: (data: any) => api.post('/bom/versions', data),
  updateVersion: (id: string, data: any) => api.put(`/bom/versions/${id}`, data),
  deleteVersion: (id: string) => api.delete(`/bom/versions/${id}`),
  releaseVersion: (id: string) => api.post(`/bom/versions/${id}/release`),
  obsoleteVersion: (id: string) => api.post(`/bom/versions/${id}/obsolete`),
  copyVersion: (id: string, data: any) => api.post(`/bom/versions/${id}/copy`, data),
  compareVersions: (id1: string, id2: string) => api.get(`/bom/versions/compare/${id1}/${id2}`),
  getProductVersions: (productId: string) => api.get(`/bom/product/${productId}/versions`),
};

// 变更日志API
export const changeLogApi = {
  getList: (params?: any) => api.get('/change-logs', { params }),
  getEntityLogs: (entityType: string, entityId: string) =>
    api.get(`/change-logs/${entityType}/${entityId}`),
};

// 统计API
export const statsApi = {
  get: () => api.get('/stats'),
};

export default api;
