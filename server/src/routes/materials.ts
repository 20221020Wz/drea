import { Router, Request, Response } from 'express';
import db from '../database';
import { v4 as uuidv4 } from 'uuid';
import { Material, ApiResponse, PaginatedResult } from '../types';
import { logChange } from '../services/changeLog';

const router = Router();

// 获取物料列表
router.get('/', (req: Request, res: Response) => {
  try {
    const { page = 1, pageSize = 20, keyword = '', category, status } = req.query;
    const offset = (Number(page) - 1) * Number(pageSize);

    let whereClause = '1=1';
    const params: any[] = [];

    if (keyword) {
      whereClause += ' AND (code LIKE ? OR name LIKE ? OR specification LIKE ?)';
      params.push(`%${keyword}%`, `%${keyword}%`, `%${keyword}%`);
    }

    if (category) {
      whereClause += ' AND category = ?';
      params.push(category);
    }

    if (status) {
      whereClause += ' AND status = ?';
      params.push(status);
    }

    const countStmt = db.prepare(`SELECT COUNT(*) as total FROM materials WHERE ${whereClause}`);
    const { total } = countStmt.get(...params) as { total: number };

    const stmt = db.prepare(`
      SELECT * FROM materials
      WHERE ${whereClause}
      ORDER BY created_at DESC
      LIMIT ? OFFSET ?
    `);

    const items = stmt.all(...params, Number(pageSize), offset) as Material[];

    const result: PaginatedResult<Material> = {
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

// 获取单个物料
router.get('/:id', (req: Request, res: Response) => {
  try {
    const stmt = db.prepare('SELECT * FROM materials WHERE id = ?');
    const material = stmt.get(req.params.id) as Material | undefined;

    if (!material) {
      return res.status(404).json({ success: false, error: '物料不存在' } as ApiResponse);
    }

    res.json({ success: true, data: material } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

// 创建物料
router.post('/', (req: Request, res: Response) => {
  try {
    const { code, name, specification, unit, category, supplier, price } = req.body;

    if (!code || !name || !unit) {
      return res.status(400).json({ success: false, error: '物料编码、名称和单位不能为空' } as ApiResponse);
    }

    // 检查编码是否重复
    const existingStmt = db.prepare('SELECT id FROM materials WHERE code = ?');
    if (existingStmt.get(code)) {
      return res.status(400).json({ success: false, error: '物料编码已存在' } as ApiResponse);
    }

    const id = uuidv4();
    const stmt = db.prepare(`
      INSERT INTO materials (id, code, name, specification, unit, category, supplier, price)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `);

    stmt.run(id, code, name, specification || null, unit, category || null, supplier || null, price || 0);

    const newMaterial = db.prepare('SELECT * FROM materials WHERE id = ?').get(id) as Material;

    // 记录变更
    logChange('material', id, 'create', null, newMaterial, req.body.operator);

    res.status(201).json({ success: true, data: newMaterial, message: '物料创建成功' } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

// 更新物料
router.put('/:id', (req: Request, res: Response) => {
  try {
    const { code, name, specification, unit, category, supplier, price, status } = req.body;

    const oldMaterial = db.prepare('SELECT * FROM materials WHERE id = ?').get(req.params.id) as Material | undefined;
    if (!oldMaterial) {
      return res.status(404).json({ success: false, error: '物料不存在' } as ApiResponse);
    }

    // 检查编码是否与其他物料重复
    if (code && code !== oldMaterial.code) {
      const existingStmt = db.prepare('SELECT id FROM materials WHERE code = ? AND id != ?');
      if (existingStmt.get(code, req.params.id)) {
        return res.status(400).json({ success: false, error: '物料编码已存在' } as ApiResponse);
      }
    }

    const stmt = db.prepare(`
      UPDATE materials SET
        code = COALESCE(?, code),
        name = COALESCE(?, name),
        specification = ?,
        unit = COALESCE(?, unit),
        category = ?,
        supplier = ?,
        price = COALESCE(?, price),
        status = COALESCE(?, status),
        updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `);

    stmt.run(
      code || null,
      name || null,
      specification !== undefined ? specification : oldMaterial.specification,
      unit || null,
      category !== undefined ? category : oldMaterial.category,
      supplier !== undefined ? supplier : oldMaterial.supplier,
      price !== undefined ? price : null,
      status || null,
      req.params.id
    );

    const updatedMaterial = db.prepare('SELECT * FROM materials WHERE id = ?').get(req.params.id) as Material;

    // 记录变更
    logChange('material', req.params.id, 'update', oldMaterial, updatedMaterial, req.body.operator);

    res.json({ success: true, data: updatedMaterial, message: '物料更新成功' } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

// 删除物料
router.delete('/:id', (req: Request, res: Response) => {
  try {
    const material = db.prepare('SELECT * FROM materials WHERE id = ?').get(req.params.id) as Material | undefined;
    if (!material) {
      return res.status(404).json({ success: false, error: '物料不存在' } as ApiResponse);
    }

    // 检查是否有关联的BOM项
    const bomItemCount = db.prepare('SELECT COUNT(*) as count FROM bom_items WHERE material_id = ?').get(req.params.id) as { count: number };
    if (bomItemCount.count > 0) {
      return res.status(400).json({ success: false, error: '该物料已被BOM引用，无法删除' } as ApiResponse);
    }

    db.prepare('DELETE FROM materials WHERE id = ?').run(req.params.id);

    // 记录变更
    logChange('material', req.params.id, 'delete', material, null, req.query.operator as string);

    res.json({ success: true, message: '物料删除成功' } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

// 获取所有物料（不分页，用于下拉选择）
router.get('/all/list', (req: Request, res: Response) => {
  try {
    const stmt = db.prepare("SELECT id, code, name, specification, unit, price FROM materials WHERE status = 'active' ORDER BY code");
    const items = stmt.all() as Material[];
    res.json({ success: true, data: items } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

// 获取物料分类列表
router.get('/categories/list', (req: Request, res: Response) => {
  try {
    const stmt = db.prepare('SELECT DISTINCT category FROM materials WHERE category IS NOT NULL ORDER BY category');
    const categories = stmt.all() as { category: string }[];
    res.json({ success: true, data: categories.map(c => c.category) } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

export default router;
