# DispatchGrid Setup Guide

## System Requirements

- **Python**: 3.11 or higher
- **Node.js**: 18+ with npm
- **RAM**: 4GB minimum
- **Storage**: 500MB free space
- **OS**: Windows, macOS, or Linux

## Step-by-Step Installation

### 1. Backend Setup

#### Create Virtual Environment

**Windows:**
```powershell
cd backend
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

#### Install Dependencies

```bash
pip install -r requirements.txt
```

Expected packages:
- FastAPI 0.104.1
- SQLAlchemy 2.0.23
- Pydantic 2.5.0
- Uvicorn 0.24.0
- pytest 7.4.3

#### Configure Environment

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Edit `.env` if needed (defaults work for local development).

#### Verify Backend Installation

```bash
# Start the server
python -m uvicorn app.main:app --reload

# Should see:
# INFO:     Uvicorn running on http://127.0.0.1:8000
# INFO:     Application startup complete
```

Test endpoints:
- `http://localhost:8000/` - Should return API info
- `http://localhost:8000/api/health` - Should return health status

### 2. Frontend Setup

#### Install Dependencies

```bash
cd frontend
npm install
```

This will install:
- React 18.2
- TypeScript 5.2
- Vite 5.0
- Tailwind CSS 3.3
- React Router 6.20
- Axios 1.6
- Recharts 2.10

#### Start Development Server

```bash
npm run dev
```

Should see:
```
  VITE v5.0.8  ready in 500 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

Open `http://localhost:3000` in your browser.

### 3. Verify Complete Setup

✅ Backend running on `http://localhost:8000`  
✅ Frontend running on `http://localhost:3000`  
✅ Frontend can connect to backend (check dashboard status)  
✅ No console errors

## Troubleshooting

### Backend Issues

**Error: `ModuleNotFoundError: No module named 'fastapi'`**
```bash
# Ensure virtual environment is activated
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Reinstall dependencies
pip install -r requirements.txt
```

**Error: `Database is locked`**
```bash
# Stop all running instances of the backend
# Delete dispatchgrid.db and restart
```

**Port 8000 already in use:**
```bash
# Change port in uvicorn command
python -m uvicorn app.main:app --reload --port 8001
```

### Frontend Issues

**Error: `npm: command not found`**
- Install Node.js from https://nodejs.org/

**Error: Port 3000 in use:**
```bash
# Vite will automatically suggest next available port
# Or specify in vite.config.ts
```

**Backend connection failed:**
- Verify backend is running on port 8000
- Check proxy configuration in `vite.config.ts`
- Check CORS settings in `app/main.py`

### Database Issues

**Want to reset database:**
```bash
cd backend
rm dispatchgrid.db
python -m uvicorn app.main:app --reload
# Database will be recreated automatically
```

## Development Workflow

### Running Both Servers

**Terminal 1 - Backend:**
```bash
cd backend
venv\Scripts\activate  # or source venv/bin/activate
python -m uvicorn app.main:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### Running Tests

```bash
cd backend
pytest

# With coverage
pytest --cov=app

# Specific test file
pytest tests/test_api_jobs.py
```

### Code Formatting (Optional)

```bash
# Backend
black app/
ruff app/

# Frontend
npm run lint
```

## Next Steps

Once setup is complete:

1. **Explore the API**: Visit `http://localhost:8000/docs`
2. **Check Phase 3**: Database models and CRUD operations
3. **Review Architecture**: See `docs/ARCHITECTURE.md`
4. **Understand Algorithm**: See Phase 1 documentation

## Quick Commands Reference

```bash
# Backend
cd backend
venv\Scripts\activate
python -m uvicorn app.main:app --reload
pytest

# Frontend
cd frontend
npm install
npm run dev
npm run build

# Database
rm dispatchgrid.db  # Reset database
```

## Support

For issues or questions:
1. Check this SETUP.md guide
2. Review README.md
3. Check Phase 1 architecture document
4. Review error messages carefully

---

**Setup Guide Version**: 1.0  
**Last Updated**: October 30, 2026
