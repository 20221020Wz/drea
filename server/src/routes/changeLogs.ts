import { Router, Request, Response } from 'express';
import { ApiResponse } from '../types';
import { getChangeLogs, getEntityChangeLogs } from '../services/changeLog';

const router = Router();

// 获取变更历史列表
router.get('/', (req: Request, res: Response) => {
  try {
    const { page = 1, pageSize = 20, entity_type, entity_id } = req.query;

    const result = getChangeLogs(
      entity_type as string | undefined,
      entity_id as string | undefined,
      Number(page),
      Number(pageSize)
    );

    res.json({ success: true, data: result } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

// 获取特定实体的变更历史
router.get('/:entityType/:entityId', (req: Request, res: Response) => {
  try {
    const { entityType, entityId } = req.params;
    const logs = getEntityChangeLogs(entityType, entityId);
    res.json({ success: true, data: logs } as ApiResponse);
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message } as ApiResponse);
  }
});

export default router;
