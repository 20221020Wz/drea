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
}

// BOM版本详情（包含产品信息）
export interface BomVersionDetail extends BomVersion {
  product_code?: string;
  product_name?: string;
  items?: BomItemDetail[];
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
}

// BOM明细详情（包含物料信息）
export interface BomItemDetail extends BomItem {
  material_code?: string;
  material_name?: string;
  material_specification?: string;
  material_price?: number;
}

// 变更日志
export interface ChangeLog {
  id: string;
  entity_type: 'product' | 'material' | 'bom_version' | 'bom_item';
  entity_id: string;
  action: 'create' | 'update' | 'delete' | 'release' | 'obsolete';
  old_value?: string;
  new_value?: string;
  changed_by?: string;
  changed_at: string;
  remark?: string;
}

// 版本比较结果
export interface VersionCompareResult {
  added: BomItemDetail[];
  removed: BomItemDetail[];
  modified: {
    item: BomItemDetail;
    oldItem: BomItemDetail;
    changes: string[];
  }[];
}

// API响应
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

// 分页参数
export interface PaginationParams {
  page?: number;
  pageSize?: number;
  keyword?: string;
}

// 分页结果
export interface PaginatedResult<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}
