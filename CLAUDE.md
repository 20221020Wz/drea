# CLAUDE.md - AI Assistant Guide for Drea Repository

## Repository Overview

This repository contains two main projects:

1. **BOM Management System** (BOM物料清单管理系统) - A full-stack enterprise BOM (Bill of Materials) management system with version control and change tracking
2. **Feishu Chat Backup Tool** - A Python utility for backing up Feishu (Lark) group chat messages

---

## Project 1: BOM Management System

### Tech Stack

**Backend (server/):**
- Node.js + Express
- TypeScript
- SQLite via better-sqlite3
- UUID for ID generation

**Frontend (client/):**
- React 18
- TypeScript
- Ant Design 5
- React Router 6
- Vite (build tool)
- Axios (HTTP client)
- Day.js (date handling)

### Architecture

```
drea/
├── package.json              # Root workspace config (concurrently)
├── server/                   # Backend API
│   ├── src/
│   │   ├── index.ts          # Express app entry, routes registration
│   │   ├── database.ts       # SQLite setup, table initialization
│   │   ├── types.ts          # TypeScript interfaces
│   │   ├── routes/           # REST API endpoints
│   │   │   ├── products.ts   # Product CRUD
│   │   │   ├── materials.ts  # Material CRUD
│   │   │   ├── bom.ts        # BOM version management
│   │   │   └── changeLogs.ts # Change history
│   │   └── services/
│   │       └── changeLog.ts  # Change logging service
│   └── data/                 # SQLite database files (gitignored)
└── client/                   # Frontend SPA
    └── src/
        ├── main.tsx          # React entry point
        ├── App.tsx           # Router configuration
        ├── api/index.ts      # API client with axios
        ├── types/index.ts    # TypeScript interfaces
        ├── components/       # Reusable components
        │   └── AppSider.tsx  # Navigation sidebar
        └── pages/            # Page components
            ├── Dashboard.tsx
            ├── Products.tsx
            ├── Materials.tsx
            ├── BomVersions.tsx
            ├── BomDetail.tsx
            ├── BomCompare.tsx
            └── ChangeLogs.tsx
```

### Database Schema

Five main tables in SQLite:
- `products` - Product master data
- `materials` - Material/component master data
- `bom_versions` - BOM versions with status (draft/released/obsolete)
- `bom_items` - BOM line items linking versions to materials
- `change_logs` - Audit trail for all entity changes

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Health check |
| `GET /api/stats` | System statistics |
| `GET/POST/PUT/DELETE /api/products` | Product CRUD |
| `GET/POST/PUT/DELETE /api/materials` | Material CRUD |
| `GET/POST/PUT/DELETE /api/bom/versions` | BOM version management |
| `POST /api/bom/versions/:id/release` | Publish BOM version |
| `POST /api/bom/versions/:id/obsolete` | Deprecate BOM version |
| `POST /api/bom/versions/:id/copy` | Clone BOM version |
| `GET /api/bom/versions/compare/:id1/:id2` | Compare two versions |
| `GET /api/change-logs` | Change history |

### Frontend Routes

| Path | Component | Description |
|------|-----------|-------------|
| `/dashboard` | Dashboard | System overview with stats |
| `/products` | Products | Product management |
| `/materials` | Materials | Material management |
| `/bom` | BomVersions | BOM version list |
| `/bom/:id` | BomDetail | BOM detail with line items |
| `/bom/compare` | BomCompare | Version comparison |
| `/change-logs` | ChangeLogs | Audit history |

### Development Commands

```bash
# Install all dependencies
npm run install:all

# Start both frontend and backend (recommended)
npm run dev

# Start backend only (port 3001)
npm run server

# Start frontend only (port 3000)
npm run client

# Build frontend for production
npm run build
```

### Key Business Logic

1. **BOM Version Status Flow:**
   - `draft` → Can edit items
   - `released` → Locked, read-only (versioned state)
   - `obsolete` → Deprecated, historical reference only

2. **Change Tracking:**
   - All CRUD operations log to `change_logs` table
   - Supports actions: create, update, delete, release, obsolete

3. **Version Comparison:**
   - Compares two BOM versions to show added/removed/modified items

---

## Project 2: Feishu Chat Backup Tool

### File: `feishu_chat_backup.py`

A standalone Python script for backing up Feishu (Lark) group chat messages.

### Dependencies
- Python 3.x
- `requests` library

### Features
- List all groups where the bot is a member
- Export messages to JSON and/or CSV format
- Download images and files from messages
- Filter by time range
- Support for multiple message types (text, image, file, rich text, etc.)

### Usage

```bash
# Configure credentials
cp .env.example .env
# Edit .env with FEISHU_APP_ID and FEISHU_APP_SECRET

# List available groups
python feishu_chat_backup.py --list-chats

# Backup specific group
python feishu_chat_backup.py --chat-id oc_xxx

# Backup all groups
python feishu_chat_backup.py --backup-all

# With time range and format options
python feishu_chat_backup.py --chat-id oc_xxx --start-time 1704067200 --end-time 1735689600 --format both

# Without downloading media files
python feishu_chat_backup.py --chat-id oc_xxx --no-download
```

### Helper Script
`run_backup.sh` - Shell wrapper that loads `.env` and checks dependencies

---

## Development Conventions

### TypeScript/JavaScript
- Use TypeScript for type safety
- Interfaces defined in `types.ts` (server) and `types/index.ts` (client)
- API responses follow `ApiResponse<T>` pattern with `success`, `data`, `error` fields
- Use UUID v4 for entity IDs

### React Patterns
- Functional components with hooks
- Ant Design components for UI
- Centralized API client in `api/index.ts`
- Page components in `pages/` directory

### Database
- SQLite with better-sqlite3 (synchronous API)
- Foreign keys enabled
- Indexes on frequently queried columns
- Soft-delete pattern not used (hard deletes with change logging)

### Error Handling
- Backend: Express error middleware returns JSON errors
- Frontend: Axios interceptor extracts error messages
- All operations should be wrapped in try/catch

### Localization
- UI is in Chinese (中文)
- Code comments may be in Chinese
- Variable names and code structure in English

---

## Environment Configuration

### `.env` (gitignored)
```
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Server Environment
- `PORT` - Backend server port (default: 3001)

---

## Common Tasks for AI Assistants

### Adding a New Entity
1. Add table schema in `server/src/database.ts`
2. Define TypeScript interfaces in `server/src/types.ts` and `client/src/types/index.ts`
3. Create route file in `server/src/routes/`
4. Register route in `server/src/index.ts`
5. Add API client functions in `client/src/api/index.ts`
6. Create page component in `client/src/pages/`
7. Add route in `client/src/App.tsx`
8. Update navigation in `client/src/components/AppSider.tsx`

### Adding API Endpoints
1. Add route handler in appropriate `server/src/routes/*.ts` file
2. Follow existing CRUD patterns
3. Use `changeLogService.log()` for audit trail
4. Return `{ success: true, data: ... }` or `{ success: false, error: ... }`

### Frontend Changes
1. Use Ant Design components (Table, Form, Modal, Button, etc.)
2. Follow existing page structure patterns
3. Use the centralized API client
4. Handle loading and error states

---

## Files to Avoid Modifying

- `server/data/*.db` - Database files (gitignored, auto-generated)
- `.env` - Contains secrets (gitignored)
- `node_modules/` - Dependencies (gitignored)
- `dist/`, `build/` - Build outputs (gitignored)

---

## Testing

No automated tests are currently configured. When adding tests:
- Consider Jest for backend unit tests
- Consider Vitest for frontend tests (Vite ecosystem)
- Consider Playwright or Cypress for E2E tests

---

## Security Notes

1. No authentication is currently implemented (internal tool assumption)
2. CORS is enabled for all origins in development
3. Never commit `.env` files
4. The Feishu backup tool handles sensitive credentials - keep App Secret secure
