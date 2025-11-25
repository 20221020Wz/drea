import { Router, Request, Response } from 'express';
import db from '../database';
import { v4 as uuidv4 } from 'uuid';
import { Product, ApiResponse, PaginatedResult } from '../types';
import { logChange } from '../services/changeLog';

const router = Router();

// 获取产品列表
router.get('/', (req: Request, res: Response) => {
  try {
    const { page = 1, pageSize = 20, keyword = '', status } = req.query;
    const offset = (Number(page) - 1) * Number(pageSize);

    let whereClause = '1=1';
    const params: any[] = [];

    if (keyword) {
      whereClause += ' AND (code LIKE ? OR name LIKE ?)';
      params.push(`%${keyword}%`, `%${keyword}%`);
    }

    if (status) {
      whereClause += ' AND status = ?';
      params.push(status);
    }

    const countStmt = db.prepare(`SELECT COUNT(*) as total FROM products WHERE ${whereClause}`);
    const { total } = countStmt.get(...params) as { total: number };

    const stmt = db.prepare(`
      SELECT * FROM products
      WHERE ${whereClause}
      ORDER BY created_at DESC
      LIMIT ? OFFSET ?
    `);

    const items = stmt.all(...params, Number(pageSize), offset) as Product[];

    const result: PaginatedResult<Product> = {
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

// 获取单个产品
router.get('/:id', (req: Request, res: Response) => {
  try {
    const stmt = db.prepare('SELECT * FROM products WHERE id = ?');
    const product = stmt.get(req.params.id) as Product | undefined;

    if (!product) {
      return res.status(404).json({ success: false, error: '产品不存在' } as ApiResponse);
    }

    res.json({ success: true, data: product } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

// 创建产品
router.post('/', (req: Request, res: Response) => {
  try {
    const { code, name, description, category } = req.body;

    if (!code || !name) {
      return res.status(400).json({ success: false, error: '产品编码和名称不能为空' } as ApiResponse);
    }

    // 检查编码是否重复
    const existingStmt = db.prepare('SELECT id FROM products WHERE code = ?');
    if (existingStmt.get(code)) {
      return res.status(400).json({ success: false, error: '产品编码已存在' } as ApiResponse);
    }

    const id = uuidv4();
    const stmt = db.prepare(`
      INSERT INTO products (id, code, name, description, category)
      VALUES (?, ?, ?, ?, ?)
    `);

    stmt.run(id, code, name, description || null, category || null);

    const newProduct = db.prepare('SELECT * FROM products WHERE id = ?').get(id) as Product;

    // 记录变更
    logChange('product', id, 'create', null, newProduct, req.body.operator);

    res.status(201).json({ success: true, data: newProduct, message: '产品创建成功' } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

// 更新产品
router.put('/:id', (req: Request, res: Response) => {
  try {
    const { code, name, description, category, status } = req.body;

    const oldProduct = db.prepare('SELECT * FROM products WHERE id = ?').get(req.params.id) as Product | undefined;
    if (!oldProduct) {
      return res.status(404).json({ success: false, error: '产品不存在' } as ApiResponse);
    }

    // 检查编码是否与其他产品重复
    if (code && code !== oldProduct.code) {
      const existingStmt = db.prepare('SELECT id FROM products WHERE code = ? AND id != ?');
      if (existingStmt.get(code, req.params.id)) {
        return res.status(400).json({ success: false, error: '产品编码已存在' } as ApiResponse);
      }
    }

    const stmt = db.prepare(`
      UPDATE products SET
        code = COALESCE(?, code),
        name = COALESCE(?, name),
        description = ?,
        category = ?,
        status = COALESCE(?, status),
        updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `);

    stmt.run(
      code || null,
      name || null,
      description !== undefined ? description : oldProduct.description,
      category !== undefined ? category : oldProduct.category,
      status || null,
      req.params.id
    );

    const updatedProduct = db.prepare('SELECT * FROM products WHERE id = ?').get(req.params.id) as Product;

    // 记录变更
    logChange('product', req.params.id, 'update', oldProduct, updatedProduct, req.body.operator);

    res.json({ success: true, data: updatedProduct, message: '产品更新成功' } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

// 删除产品
router.delete('/:id', (req: Request, res: Response) => {
  try {
    const product = db.prepare('SELECT * FROM products WHERE id = ?').get(req.params.id) as Product | undefined;
    if (!product) {
      return res.status(404).json({ success: false, error: '产品不存在' } as ApiResponse);
    }

    // 检查是否有关联的BOM版本
    const bomCount = db.prepare('SELECT COUNT(*) as count FROM bom_versions WHERE product_id = ?').get(req.params.id) as { count: number };
    if (bomCount.count > 0) {
      return res.status(400).json({ success: false, error: '该产品存在关联的BOM版本，无法删除' } as ApiResponse);
    }

    db.prepare('DELETE FROM products WHERE id = ?').run(req.params.id);

    // 记录变更
    logChange('product', req.params.id, 'delete', product, null, req.query.operator as string);

    res.json({ success: true, message: '产品删除成功' } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

// 获取所有产品（不分页，用于下拉选择）
router.get('/all/list', (req: Request, res: Response) => {
  try {
    const stmt = db.prepare("SELECT id, code, name FROM products WHERE status = 'active' ORDER BY code");
    const items = stmt.all() as Product[];
    res.json({ success: true, data: items } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

export default router;
