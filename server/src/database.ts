import Database from 'better-sqlite3';
import path from 'path';

const dbPath = path.join(__dirname, '..', 'data', 'bom.db');

// 确保数据目录存在
import fs from 'fs';
const dataDir = path.dirname(dbPath);
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

const db = new Database(dbPath);

// 启用外键约束
db.pragma('foreign_keys = ON');

// 初始化数据库表
export function initDatabase() {
  // 产品表
  db.exec(`
    CREATE TABLE IF NOT EXISTS products (
      id TEXT PRIMARY KEY,
      code TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL,
      description TEXT,
      category TEXT,
      status TEXT DEFAULT 'active',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `);

  // 物料表
  db.exec(`
    CREATE TABLE IF NOT EXISTS materials (
      id TEXT PRIMARY KEY,
      code TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL,
      specification TEXT,
      unit TEXT NOT NULL,
      category TEXT,
      supplier TEXT,
      price REAL DEFAULT 0,
      status TEXT DEFAULT 'active',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `);

  // BOM版本表
  db.exec(`
    CREATE TABLE IF NOT EXISTS bom_versions (
      id TEXT PRIMARY KEY,
      product_id TEXT NOT NULL,
      version TEXT NOT NULL,
      status TEXT DEFAULT 'draft',
      description TEXT,
      created_by TEXT,
      released_at DATETIME,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (product_id) REFERENCES products(id),
      UNIQUE(product_id, version)
    )
  `);

  // BOM明细表
  db.exec(`
    CREATE TABLE IF NOT EXISTS bom_items (
      id TEXT PRIMARY KEY,
      bom_version_id TEXT NOT NULL,
      material_id TEXT NOT NULL,
      quantity REAL NOT NULL,
      unit TEXT NOT NULL,
      position TEXT,
      remark TEXT,
      sort_order INTEGER DEFAULT 0,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (bom_version_id) REFERENCES bom_versions(id) ON DELETE CASCADE,
      FOREIGN KEY (material_id) REFERENCES materials(id)
    )
  `);

  // 变更历史表
  db.exec(`
    CREATE TABLE IF NOT EXISTS change_logs (
      id TEXT PRIMARY KEY,
      entity_type TEXT NOT NULL,
      entity_id TEXT NOT NULL,
      action TEXT NOT NULL,
      old_value TEXT,
      new_value TEXT,
      changed_by TEXT,
      changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      remark TEXT
    )
  `);

  // 创建索引
  db.exec(`
    CREATE INDEX IF NOT EXISTS idx_bom_versions_product ON bom_versions(product_id);
    CREATE INDEX IF NOT EXISTS idx_bom_items_version ON bom_items(bom_version_id);
    CREATE INDEX IF NOT EXISTS idx_change_logs_entity ON change_logs(entity_type, entity_id);
  `);

  console.log('数据库初始化完成');
}

export default db;
