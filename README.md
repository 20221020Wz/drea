# BOM物料清单管理系统

企业内部产品BOM（物料清单）管理系统，支持版本控制和变更追踪。

## 功能特性

- **产品管理**: 产品信息的增删改查
- **物料管理**: 物料基础信息管理，包括编码、名称、规格、单价等
- **BOM版本管理**:
  - 为每个产品创建多个BOM版本
  - 支持草稿、发布、废弃三种状态
  - 发布后的版本不可修改，确保数据一致性
  - 支持版本复制，快速创建新版本
- **版本对比**: 比较两个BOM版本之间的差异（新增、删除、修改的物料）
- **变更历史**: 记录所有数据变更，支持追溯

## 技术栈

### 后端
- Node.js + Express
- TypeScript
- SQLite (better-sqlite3)

### 前端
- React 18
- TypeScript
- Ant Design 5
- React Router 6
- Vite

## 快速开始

### 安装依赖

```bash
# 安装所有依赖
npm run install:all
```

或分别安装：

```bash
# 安装根目录依赖
npm install

# 安装后端依赖
cd server && npm install

# 安装前端依赖
cd ../client && npm install
```

### 启动开发服务器

```bash
# 同时启动前后端
npm run dev
```

或分别启动：

```bash
# 启动后端服务 (端口 3001)
npm run server

# 启动前端服务 (端口 3000)
npm run client
```

### 访问系统

打开浏览器访问 `http://localhost:3000`

## 项目结构

```
bom-management-system/
├── package.json          # 根目录配置
├── server/               # 后端服务
│   ├── src/
│   │   ├── index.ts      # 入口文件
│   │   ├── database.ts   # 数据库配置
│   │   ├── types.ts      # 类型定义
│   │   ├── routes/       # API路由
│   │   │   ├── products.ts
│   │   │   ├── materials.ts
│   │   │   ├── bom.ts
│   │   │   └── changeLogs.ts
│   │   └── services/     # 业务服务
│   │       └── changeLog.ts
│   └── data/             # 数据库文件目录
└── client/               # 前端应用
    ├── src/
    │   ├── main.tsx      # 入口文件
    │   ├── App.tsx       # 主组件
    │   ├── api/          # API封装
    │   ├── types/        # 类型定义
    │   ├── components/   # 公共组件
    │   └── pages/        # 页面组件
    │       ├── Dashboard.tsx
    │       ├── Products.tsx
    │       ├── Materials.tsx
    │       ├── BomVersions.tsx
    │       ├── BomDetail.tsx
    │       ├── BomCompare.tsx
    │       └── ChangeLogs.tsx
    └── index.html
```

## API接口

### 产品管理
- `GET /api/products` - 获取产品列表
- `GET /api/products/:id` - 获取单个产品
- `POST /api/products` - 创建产品
- `PUT /api/products/:id` - 更新产品
- `DELETE /api/products/:id` - 删除产品

### 物料管理
- `GET /api/materials` - 获取物料列表
- `GET /api/materials/:id` - 获取单个物料
- `POST /api/materials` - 创建物料
- `PUT /api/materials/:id` - 更新物料
- `DELETE /api/materials/:id` - 删除物料

### BOM版本管理
- `GET /api/bom/versions` - 获取BOM版本列表
- `GET /api/bom/versions/:id` - 获取BOM版本详情（含明细）
- `POST /api/bom/versions` - 创建BOM版本
- `PUT /api/bom/versions/:id` - 更新BOM版本
- `DELETE /api/bom/versions/:id` - 删除BOM版本
- `POST /api/bom/versions/:id/release` - 发布BOM版本
- `POST /api/bom/versions/:id/obsolete` - 废弃BOM版本
- `POST /api/bom/versions/:id/copy` - 复制BOM版本
- `GET /api/bom/versions/compare/:id1/:id2` - 版本对比

### 变更历史
- `GET /api/change-logs` - 获取变更历史列表
- `GET /api/change-logs/:entityType/:entityId` - 获取实体变更历史

## 使用说明

### BOM版本状态流转

1. **草稿 (draft)**: 新创建的BOM版本，可以编辑物料明细
2. **已发布 (released)**: 发布后的版本，物料清单被锁定不可修改
3. **已废弃 (obsolete)**: 不再使用的版本，仅供历史查阅

### 操作流程

1. 先创建产品和物料基础数据
2. 为产品创建BOM版本
3. 在BOM详情页添加物料明细
4. 确认无误后发布版本
5. 需要修改时，从已发布版本复制创建新版本
