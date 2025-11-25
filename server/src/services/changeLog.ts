import db from '../database';
import { v4 as uuidv4 } from 'uuid';
import { ChangeLog, ApiResponse, PaginatedResult } from '../types';

// 记录变更
export function logChange(
  entityType: string,
  entityId: string,
  action: string,
  oldValue: any,
  newValue: any,
  changedBy?: string,
  remark?: string
): void {
  const stmt = db.prepare(`
    INSERT INTO change_logs (id, entity_type, entity_id, action, old_value, new_value, changed_by, remark)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `);

  stmt.run(
    uuidv4(),
    entityType,
    entityId,
    action,
    oldValue ? JSON.stringify(oldValue) : null,
    newValue ? JSON.stringify(newValue) : null,
    changedBy || null,
    remark || null
  );
}

// 获取变更历史
export function getChangeLogs(
  entityType?: string,
  entityId?: string,
  page: number = 1,
  pageSize: number = 20
): PaginatedResult<ChangeLog> {
  const offset = (page - 1) * pageSize;

  let whereClause = '1=1';
  const params: any[] = [];

  if (entityType) {
    whereClause += ' AND entity_type = ?';
    params.push(entityType);
  }

  if (entityId) {
    whereClause += ' AND entity_id = ?';
    params.push(entityId);
  }

  const countStmt = db.prepare(`SELECT COUNT(*) as total FROM change_logs WHERE ${whereClause}`);
  const { total } = countStmt.get(...params) as { total: number };

  const stmt = db.prepare(`
    SELECT * FROM change_logs
    WHERE ${whereClause}
    ORDER BY changed_at DESC
    LIMIT ? OFFSET ?
  `);

  const items = stmt.all(...params, pageSize, offset) as ChangeLog[];

  // 解析JSON字段
  items.forEach(item => {
    if (item.old_value) {
      try {
        (item as any).old_value_parsed = JSON.parse(item.old_value);
      } catch (e) {
        // 忽略解析错误
      }
    }
    if (item.new_value) {
      try {
        (item as any).new_value_parsed = JSON.parse(item.new_value);
      } catch (e) {
        // 忽略解析错误
      }
    }
  });

  return {
    items,
    total,
    page,
    pageSize,
    totalPages: Math.ceil(total / pageSize)
  };
}

// 获取实体的变更历史
export function getEntityChangeLogs(entityType: string, entityId: string): ChangeLog[] {
  const stmt = db.prepare(`
    SELECT * FROM change_logs
    WHERE entity_type = ? AND entity_id = ?
    ORDER BY changed_at DESC
  `);

  const items = stmt.all(entityType, entityId) as ChangeLog[];

  // 解析JSON字段
  items.forEach(item => {
    if (item.old_value) {
      try {
        (item as any).old_value_parsed = JSON.parse(item.old_value);
      } catch (e) {
        // 忽略解析错误
      }
    }
    if (item.new_value) {
      try {
        (item as any).new_value_parsed = JSON.parse(item.new_value);
      } catch (e) {
        // 忽略解析错误
      }
    }
  });

  return items;
}
