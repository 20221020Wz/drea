import { Router, Request, Response } from 'express';
import db from '../database';
import { v4 as uuidv4 } from 'uuid';
import { BomVersion, BomVersionDetail, BomItem, BomItemDetail, ApiResponse, PaginatedResult, VersionCompareResult } from '../types';
import { logChange } from '../services/changeLog';

const router = Router();

// 获取BOM版本列表
router.get('/versions', (req: Request, res: Response) => {
  try {
    const { page = 1, pageSize = 20, product_id, status, keyword } = req.query;
    const offset = (Number(page) - 1) * Number(pageSize);

    let whereClause = '1=1';
    const params: any[] = [];

    if (product_id) {
      whereClause += ' AND bv.product_id = ?';
      params.push(product_id);
    }

    if (status) {
      whereClause += ' AND bv.status = ?';
      params.push(status);
    }

    if (keyword) {
      whereClause += ' AND (p.code LIKE ? OR p.name LIKE ? OR bv.version LIKE ?)';
      params.push(`%${keyword}%`, `%${keyword}%`, `%${keyword}%`);
    }

    const countStmt = db.prepare(`
      SELECT COUNT(*) as total FROM bom_versions bv
      LEFT JOIN products p ON bv.product_id = p.id
      WHERE ${whereClause}
    `);
    const { total } = countStmt.get(...params) as { total: number };

    const stmt = db.prepare(`
      SELECT bv.*, p.code as product_code, p.name as product_name
      FROM bom_versions bv
      LEFT JOIN products p ON bv.product_id = p.id
      WHERE ${whereClause}
      ORDER BY bv.created_at DESC
      LIMIT ? OFFSET ?
    `);

    const items = stmt.all(...params, Number(pageSize), offset) as BomVersionDetail[];

    const result: PaginatedResult<BomVersionDetail> = {
      items,
      total,
      page: Number(page),
      pageSize: Number(pageSize),
      totalPages: Math.ceil(total / Number(pageSize))
    };

    res.json({ success: true, data: result } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

// 获取单个BOM版本详情（含明细）
router.get('/versions/:id', (req: Request, res: Response) => {
  try {
    const versionStmt = db.prepare(`
      SELECT bv.*, p.code as product_code, p.name as product_name
      FROM bom_versions bv
      LEFT JOIN products p ON bv.product_id = p.id
      WHERE bv.id = ?
    `);
    const version = versionStmt.get(req.params.id) as BomVersionDetail | undefined;

    if (!version) {
      return res.status(404).json({ success: false, error: 'BOM版本不存在' } as ApiResponse);
    }

    // 获取明细
    const itemsStmt = db.prepare(`
      SELECT bi.*, m.code as material_code, m.name as material_name,
             m.specification as material_specification, m.price as material_price
      FROM bom_items bi
      LEFT JOIN materials m ON bi.material_id = m.id
      WHERE bi.bom_version_id = ?
      ORDER BY bi.sort_order, bi.created_at
    `);
    version.items = itemsStmt.all(req.params.id) as BomItemDetail[];

    res.json({ success: true, data: version } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

// 创建BOM版本
router.post('/versions', (req: Request, res: Response) => {
  try {
    const { product_id, version, description, created_by, items } = req.body;

    if (!product_id || !version) {
      return res.status(400).json({ success: false, error: '产品ID和版本号不能为空' } as ApiResponse);
    }

    // 检查产品是否存在
    const productStmt = db.prepare('SELECT id FROM products WHERE id = ?');
    if (!productStmt.get(product_id)) {
      return res.status(400).json({ success: false, error: '产品不存在' } as ApiResponse);
    }

    // 检查版本号是否重复
    const existingStmt = db.prepare('SELECT id FROM bom_versions WHERE product_id = ? AND version = ?');
    if (existingStmt.get(product_id, version)) {
      return res.status(400).json({ success: false, error: '该产品已存在相同版本号的BOM' } as ApiResponse);
    }

    const id = uuidv4();

    // 使用事务
    const transaction = db.transaction(() => {
      // 创建版本
      db.prepare(`
        INSERT INTO bom_versions (id, product_id, version, description, created_by)
        VALUES (?, ?, ?, ?, ?)
      `).run(id, product_id, version, description || null, created_by || null);

      // 创建明细
      if (items && Array.isArray(items) && items.length > 0) {
        const itemStmt = db.prepare(`
          INSERT INTO bom_items (id, bom_version_id, material_id, quantity, unit, position, remark, sort_order)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        `);

        items.forEach((item: any, index: number) => {
          itemStmt.run(
            uuidv4(),
            id,
            item.material_id,
            item.quantity,
            item.unit,
            item.position || null,
            item.remark || null,
            item.sort_order ?? index
          );
        });
      }
    });

    transaction();

    // 获取完整信息
    const newVersion = db.prepare(`
      SELECT bv.*, p.code as product_code, p.name as product_name
      FROM bom_versions bv
      LEFT JOIN products p ON bv.product_id = p.id
      WHERE bv.id = ?
    `).get(id) as BomVersionDetail;

    // 记录变更
    logChange('bom_version', id, 'create', null, newVersion, created_by);

    res.status(201).json({ success: true, data: newVersion, message: 'BOM版本创建成功' } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

// 更新BOM版本
router.put('/versions/:id', (req: Request, res: Response) => {
  try {
    const { version, description, items } = req.body;

    const oldVersion = db.prepare('SELECT * FROM bom_versions WHERE id = ?').get(req.params.id) as BomVersion | undefined;
    if (!oldVersion) {
      return res.status(404).json({ success: false, error: 'BOM版本不存在' } as ApiResponse);
    }

    // 检查是否为草稿状态
    if (oldVersion.status !== 'draft') {
      return res.status(400).json({ success: false, error: '只能修改草稿状态的BOM版本' } as ApiResponse);
    }

    // 检查版本号是否与其他记录重复
    if (version && version !== oldVersion.version) {
      const existingStmt = db.prepare('SELECT id FROM bom_versions WHERE product_id = ? AND version = ? AND id != ?');
      if (existingStmt.get(oldVersion.product_id, version, req.params.id)) {
        return res.status(400).json({ success: false, error: '该产品已存在相同版本号的BOM' } as ApiResponse);
      }
    }

    const transaction = db.transaction(() => {
      // 更新版本信息
      db.prepare(`
        UPDATE bom_versions SET
          version = COALESCE(?, version),
          description = ?,
          updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
      `).run(
        version || null,
        description !== undefined ? description : oldVersion.description,
        req.params.id
      );

      // 更新明细
      if (items && Array.isArray(items)) {
        // 删除旧明细
        db.prepare('DELETE FROM bom_items WHERE bom_version_id = ?').run(req.params.id);

        // 插入新明细
        const itemStmt = db.prepare(`
          INSERT INTO bom_items (id, bom_version_id, material_id, quantity, unit, position, remark, sort_order)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        `);

        items.forEach((item: any, index: number) => {
          itemStmt.run(
            item.id || uuidv4(),
            req.params.id,
            item.material_id,
            item.quantity,
            item.unit,
            item.position || null,
            item.remark || null,
            item.sort_order ?? index
          );
        });
      }
    });

    transaction();

    const updatedVersion = db.prepare(`
      SELECT bv.*, p.code as product_code, p.name as product_name
      FROM bom_versions bv
      LEFT JOIN products p ON bv.product_id = p.id
      WHERE bv.id = ?
    `).get(req.params.id) as BomVersionDetail;

    // 记录变更
    logChange('bom_version', req.params.id, 'update', oldVersion, updatedVersion, req.body.operator);

    res.json({ success: true, data: updatedVersion, message: 'BOM版本更新成功' } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

// 发布BOM版本
router.post('/versions/:id/release', (req: Request, res: Response) => {
  try {
    const version = db.prepare('SELECT * FROM bom_versions WHERE id = ?').get(req.params.id) as BomVersion | undefined;
    if (!version) {
      return res.status(404).json({ success: false, error: 'BOM版本不存在' } as ApiResponse);
    }

    if (version.status !== 'draft') {
      return res.status(400).json({ success: false, error: '只能发布草稿状态的BOM版本' } as ApiResponse);
    }

    // 检查是否有明细
    const itemCount = db.prepare('SELECT COUNT(*) as count FROM bom_items WHERE bom_version_id = ?').get(req.params.id) as { count: number };
    if (itemCount.count === 0) {
      return res.status(400).json({ success: false, error: 'BOM版本没有任何明细，无法发布' } as ApiResponse);
    }

    db.prepare(`
      UPDATE bom_versions SET
        status = 'released',
        released_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `).run(req.params.id);

    const updatedVersion = db.prepare('SELECT * FROM bom_versions WHERE id = ?').get(req.params.id) as BomVersion;

    // 记录变更
    logChange('bom_version', req.params.id, 'release', version, updatedVersion, req.body.operator);

    res.json({ success: true, data: updatedVersion, message: 'BOM版本发布成功' } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

// 废弃BOM版本
router.post('/versions/:id/obsolete', (req: Request, res: Response) => {
  try {
    const version = db.prepare('SELECT * FROM bom_versions WHERE id = ?').get(req.params.id) as BomVersion | undefined;
    if (!version) {
      return res.status(404).json({ success: false, error: 'BOM版本不存在' } as ApiResponse);
    }

    if (version.status === 'obsolete') {
      return res.status(400).json({ success: false, error: 'BOM版本已经是废弃状态' } as ApiResponse);
    }

    db.prepare(`
      UPDATE bom_versions SET
        status = 'obsolete',
        updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `).run(req.params.id);

    const updatedVersion = db.prepare('SELECT * FROM bom_versions WHERE id = ?').get(req.params.id) as BomVersion;

    // 记录变更
    logChange('bom_version', req.params.id, 'obsolete', version, updatedVersion, req.body.operator);

    res.json({ success: true, data: updatedVersion, message: 'BOM版本已废弃' } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

// 删除BOM版本
router.delete('/versions/:id', (req: Request, res: Response) => {
  try {
    const version = db.prepare('SELECT * FROM bom_versions WHERE id = ?').get(req.params.id) as BomVersion | undefined;
    if (!version) {
      return res.status(404).json({ success: false, error: 'BOM版本不存在' } as ApiResponse);
    }

    if (version.status !== 'draft') {
      return res.status(400).json({ success: false, error: '只能删除草稿状态的BOM版本' } as ApiResponse);
    }

    // 删除版本（明细会级联删除）
    db.prepare('DELETE FROM bom_versions WHERE id = ?').run(req.params.id);

    // 记录变更
    logChange('bom_version', req.params.id, 'delete', version, null, req.query.operator as string);

    res.json({ success: true, message: 'BOM版本删除成功' } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

// 复制BOM版本
router.post('/versions/:id/copy', (req: Request, res: Response) => {
  try {
    const { new_version, description, created_by } = req.body;

    const sourceVersion = db.prepare(`
      SELECT bv.*, p.code as product_code, p.name as product_name
      FROM bom_versions bv
      LEFT JOIN products p ON bv.product_id = p.id
      WHERE bv.id = ?
    `).get(req.params.id) as BomVersionDetail | undefined;

    if (!sourceVersion) {
      return res.status(404).json({ success: false, error: '源BOM版本不存在' } as ApiResponse);
    }

    if (!new_version) {
      return res.status(400).json({ success: false, error: '新版本号不能为空' } as ApiResponse);
    }

    // 检查新版本号是否重复
    const existingStmt = db.prepare('SELECT id FROM bom_versions WHERE product_id = ? AND version = ?');
    if (existingStmt.get(sourceVersion.product_id, new_version)) {
      return res.status(400).json({ success: false, error: '该产品已存在相同版本号的BOM' } as ApiResponse);
    }

    const newId = uuidv4();

    const transaction = db.transaction(() => {
      // 复制版本
      db.prepare(`
        INSERT INTO bom_versions (id, product_id, version, description, created_by, status)
        VALUES (?, ?, ?, ?, ?, 'draft')
      `).run(newId, sourceVersion.product_id, new_version, description || sourceVersion.description, created_by || null);

      // 复制明细
      const sourceItems = db.prepare('SELECT * FROM bom_items WHERE bom_version_id = ?').all(req.params.id) as BomItem[];

      const itemStmt = db.prepare(`
        INSERT INTO bom_items (id, bom_version_id, material_id, quantity, unit, position, remark, sort_order)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `);

      sourceItems.forEach((item) => {
        itemStmt.run(
          uuidv4(),
          newId,
          item.material_id,
          item.quantity,
          item.unit,
          item.position,
          item.remark,
          item.sort_order
        );
      });
    });

    transaction();

    const newVersion = db.prepare(`
      SELECT bv.*, p.code as product_code, p.name as product_name
      FROM bom_versions bv
      LEFT JOIN products p ON bv.product_id = p.id
      WHERE bv.id = ?
    `).get(newId) as BomVersionDetail;

    // 记录变更
    logChange('bom_version', newId, 'create', null, { ...newVersion, copied_from: req.params.id }, created_by);

    res.status(201).json({ success: true, data: newVersion, message: 'BOM版本复制成功' } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

// 比较两个BOM版本
router.get('/versions/compare/:id1/:id2', (req: Request, res: Response) => {
  try {
    const { id1, id2 } = req.params;

    // 获取两个版本的明细
    const getItems = (versionId: string): BomItemDetail[] => {
      return db.prepare(`
        SELECT bi.*, m.code as material_code, m.name as material_name,
               m.specification as material_specification, m.price as material_price
        FROM bom_items bi
        LEFT JOIN materials m ON bi.material_id = m.id
        WHERE bi.bom_version_id = ?
        ORDER BY bi.sort_order
      `).all(versionId) as BomItemDetail[];
    };

    const items1 = getItems(id1);
    const items2 = getItems(id2);

    // 创建物料ID到明细的映射
    const map1 = new Map(items1.map(item => [item.material_id, item]));
    const map2 = new Map(items2.map(item => [item.material_id, item]));

    const result: VersionCompareResult = {
      added: [],     // 版本2新增的
      removed: [],   // 版本2删除的
      modified: []   // 修改的
    };

    // 找出删除和修改的项
    items1.forEach(item1 => {
      const item2 = map2.get(item1.material_id);
      if (!item2) {
        result.removed.push(item1);
      } else {
        // 检查是否有修改
        const changes: string[] = [];
        if (item1.quantity !== item2.quantity) {
          changes.push(`数量: ${item1.quantity} -> ${item2.quantity}`);
        }
        if (item1.unit !== item2.unit) {
          changes.push(`单位: ${item1.unit} -> ${item2.unit}`);
        }
        if (item1.position !== item2.position) {
          changes.push(`位号: ${item1.position || '无'} -> ${item2.position || '无'}`);
        }
        if (item1.remark !== item2.remark) {
          changes.push(`备注: ${item1.remark || '无'} -> ${item2.remark || '无'}`);
        }

        if (changes.length > 0) {
          result.modified.push({ item: item2, oldItem: item1, changes });
        }
      }
    });

    // 找出新增的项
    items2.forEach(item2 => {
      if (!map1.has(item2.material_id)) {
        result.added.push(item2);
      }
    });

    res.json({ success: true, data: result } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

// 获取产品的所有BOM版本
router.get('/product/:productId/versions', (req: Request, res: Response) => {
  try {
    const stmt = db.prepare(`
      SELECT bv.*, p.code as product_code, p.name as product_name
      FROM bom_versions bv
      LEFT JOIN products p ON bv.product_id = p.id
      WHERE bv.product_id = ?
      ORDER BY bv.created_at DESC
    `);

    const versions = stmt.all(req.params.productId) as BomVersionDetail[];
    res.json({ success: true, data: versions } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

export default router;
