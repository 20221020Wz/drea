// 产品
export interface Product {
  id: string;
  code: string;
  name: string;
  description?: string;
  category?: string;
  status: 'active' | 'inactive';
  created_at: string;
  updated_at: string;
}

// 物料
export interface Material {
  id: string;
  code: string;
  name: string;
  specification?: string;
  unit: string;
  category?: string;
  supplier?: string;
  price: number;
  status: 'active' | 'inactive';
  created_at: string;
  updated_at: string;
}

// BOM版本
export interface BomVersion {
  id: string;
  product_id: string;
  version: string;
  status: 'draft' | 'released' | 'obsolete';
  description?: string;
  created_by?: string;
  released_at?: string;
  created_at: string;
  updated_at: string;
  product_code?: string;
  product_name?: string;
  items?: BomItem[];
}

// BOM明细
export interface BomItem {
  id: string;
  bom_version_id: string;
  material_id: string;
  quantity: number;
  unit: string;
  position?: string;
  remark?: string;
  sort_order: number;
  created_at: string;
  material_code?: string;
  material_name?: string;
  material_specification?: string;
  material_price?: number;
}

// 变更日志
export interface ChangeLog {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  old_value?: string;
  new_value?: string;
  old_value_parsed?: any;
  new_value_parsed?: any;
  changed_by?: string;
  changed_at: string;
  remark?: string;
}

// 版本比较结果
export interface VersionCompareResult {
  added: BomItem[];
  removed: BomItem[];
  modified: {
    item: BomItem;
    oldItem: BomItem;
    changes: string[];
  }[];
}

// 分页结果
export interface PaginatedResult<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// API响应
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

// 统计数据
export interface Stats {
  productCount: number;
  materialCount: number;
  bomVersionCount: number;
  releasedBomCount: number;
}
