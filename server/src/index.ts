import express from 'express';
import cors from 'cors';
import { initDatabase } from './database';

// 导入路由
import productsRouter from './routes/products';
import materialsRouter from './routes/materials';
import bomRouter from './routes/bom';
import changeLogsRouter from './routes/changeLogs';

const app = express();
const PORT = process.env.PORT || 3001;

// 中间件
app.use(cors());
app.use(express.json());

// 初始化数据库
initDatabase();

// 注册路由
app.use('/api/products', productsRouter);
app.use('/api/materials', materialsRouter);
app.use('/api/bom', bomRouter);
app.use('/api/change-logs', changeLogsRouter);

// 健康检查
app.get('/api/health', (req, res) => {
  res.json({ success: true, message: 'BOM管理系统服务运行正常', timestamp: new Date().toISOString() });
});

// 统计接口
app.get('/api/stats', (req, res) => {
  try {
    const db = require('./database').default;

    const productCount = (db.prepare('SELECT COUNT(*) as count FROM products').get() as { count: number }).count;
    const materialCount = (db.prepare('SELECT COUNT(*) as count FROM materials').get() as { count: number }).count;
    const bomVersionCount = (db.prepare('SELECT COUNT(*) as count FROM bom_versions').get() as { count: number }).count;
    const releasedBomCount = (db.prepare("SELECT COUNT(*) as count FROM bom_versions WHERE status = 'released'").get() as { count: number }).count;

    res.json({
      success: true,
      data: {
        productCount,
        materialCount,
        bomVersionCount,
        releasedBomCount
      }
    });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// 错误处理中间件
app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error('服务器错误:', err);
  res.status(500).json({ success: false, error: '服务器内部错误' });
});

// 启动服务器
app.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════════════════════╗
║            BOM物料清单管理系统 - 后端服务                    ║
╠════════════════════════════════════════════════════════════╣
║  服务地址: http://localhost:${PORT}                           ║
║  API文档: http://localhost:${PORT}/api                        ║
╠════════════════════════════════════════════════════════════╣
║  接口列表:                                                   ║
║  • GET    /api/health          - 健康检查                    ║
║  • GET    /api/stats           - 系统统计                    ║
║  • GET    /api/products        - 产品列表                    ║
║  • GET    /api/materials       - 物料列表                    ║
║  • GET    /api/bom/versions    - BOM版本列表                 ║
║  • GET    /api/change-logs     - 变更历史                    ║
╚════════════════════════════════════════════════════════════╝
  `);
});

export default app;
