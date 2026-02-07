# COMP Shop 数据采集自动化系统

市场部竞品数据采集与Gap分析自动化平台。

## 功能概述

- **自动数据采集**: 从Home Depot、Walmart、Lowe's、Harbor Freight四大零售商自动采集产品数据
- **AI辅助分析**: 利用Claude API进行规格提取、维度推荐和数据清洗
- **Gap分析引擎**: 自动识别完全空缺、品牌空缺、价格带空缺和功能空缺
- **Excel报告导出**: 一键生成包含原始数据、横向对比矩阵和Gap分析的Excel报告
- **飞书集成**: 任务进度通知、分析报告推送、设计需求对接
- **REST API**: 完整的任务管理和数据查询接口

## 快速开始

### 环境准备

```bash
cd comp-shop
pip install -e .
playwright install chromium
```

### 配置

```bash
cp .env.example .env
# 编辑 .env 填入必要的配置
```

### 初始化数据库

```bash
comp-shop init-db
```

### 启动API服务

```bash
comp-shop serve --reload
```

### 命令行使用

```bash
# 采集单个零售商数据
comp-shop scrape homedepot "pliers,locking pliers" -o output.xlsx

# AI关键词扩展
comp-shop expand-keywords plier

# 执行Gap分析
comp-shop analyze homedepot --dimensions size,type -o report.xlsx
```

### API使用

```bash
# 创建采集任务
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"category": "plier", "retailers": ["homedepot", "walmart", "lowes", "harborfreight"]}'

# 查询任务状态
curl http://localhost:8000/api/tasks/1

# 获取Gap分析结果
curl "http://localhost:8000/api/gaps/1?target=walmart"

# 执行Gap分析
curl -X POST http://localhost:8000/api/gaps/analyze \
  -H "Content-Type: application/json" \
  -d '{"task_id": 1, "target_retailer": "walmart", "dimensions": ["size", "type"]}'
```

## 项目结构

```
comp-shop/
├── comp_shop/
│   ├── scrapers/          # 零售商爬虫适配器
│   │   ├── base.py        # 爬虫基类
│   │   ├── homedepot.py   # Home Depot适配器
│   │   ├── walmart.py     # Walmart适配器
│   │   ├── lowes.py       # Lowe's适配器
│   │   └── harborfreight.py # Harbor Freight适配器
│   ├── ai/                # AI辅助处理
│   │   ├── prompts.py     # Prompt模板
│   │   └── processor.py   # Claude API处理器
│   ├── analysis/          # 分析引擎
│   │   └── gap_analyzer.py # Gap分析
│   ├── export/            # 数据导出
│   │   └── excel.py       # Excel生成
│   ├── integrations/      # 外部集成
│   │   └── feishu.py      # 飞书机器人
│   ├── api/               # REST API
│   │   └── routes/        # API路由
│   ├── tasks/             # 任务调度
│   ├── models.py          # 数据库模型
│   ├── config.py          # 配置管理
│   └── cli.py             # 命令行入口
├── tests/                 # 测试
├── alembic/               # 数据库迁移
└── pyproject.toml         # 项目配置
```

## 技术栈

- **爬虫**: Playwright (支持动态渲染和反检测)
- **数据处理**: Pandas + OpenPyXL
- **AI**: Anthropic Claude API
- **API**: FastAPI + Uvicorn
- **数据库**: PostgreSQL / SQLite (开发)
- **ORM**: SQLAlchemy + Alembic
- **通知**: 飞书Webhook

## 运行测试

```bash
cd comp-shop
pip install -e ".[dev]"
pytest tests/ -v
```
