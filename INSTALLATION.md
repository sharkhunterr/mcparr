# Installation Guide - MCParr AI Gateway

## Prerequisites

### System Requirements
- **Node.js**: Version 20.19+ or 22.12+ (Required for Vite frontend)
- **Python**: Version 3.9+ (Required for FastAPI backend)
- **Git**: For cloning the repository

### Check Current Versions
```bash
node --version    # Should be 20.19+ or 22.12+
python3 --version # Should be 3.9+
npm --version
```

## Installation Steps

### 1. Clone the Repository
```bash
git clone <repository-url>
cd ia-homelab/ia-homelab
```

### 2. Backend Setup (Python/FastAPI)

#### Create Virtual Environment
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Install Dependencies
```bash
pip install -r requirements.txt
```

If requirements.txt doesn't exist yet, install manually:
```bash
pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary python-multipart websockets psutil python-dotenv pydantic-settings
```

#### Environment Configuration
```bash
cp .env.example .env
# Edit .env with your database and configuration settings
```

#### Database Setup
```bash
# Initialize Alembic (if not already done)
alembic init alembic

# Create and run migrations
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

#### Start Backend Server
```bash
python3 src/main.py
# Or using uvicorn directly:
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Setup (React/TypeScript)

#### Navigate to Frontend Directory
```bash
cd ../frontend
```

#### Install Node.js Dependencies
```bash
npm install
```

#### Start Development Server
```bash
npm run dev
```

### 4. Verification

#### Check Services
- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:5173
- **API Documentation**: http://localhost:8000/docs

#### Test WebSocket Connection
Open browser dev tools and check for WebSocket connections to the backend.

## Troubleshooting

### Node.js Version Issues
If you get "Vite requires Node.js version 20.19+ or 22.12+":
```bash
# Install Node Version Manager (nvm)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc

# Install and use Node.js 20+
nvm install 20
nvm use 20
```

### Python Module Issues
If you get "ModuleNotFoundError":
```bash
# Ensure virtual environment is activated
source backend/venv/bin/activate

# Install missing dependencies
pip install fastapi uvicorn sqlalchemy
```

### Database Connection Issues
- Check `.env` file configuration
- Ensure PostgreSQL is running (if using PostgreSQL)
- For development, SQLite is used by default

### Port Conflicts
If ports 8000 or 5173 are in use:
```bash
# Backend - change port in src/main.py or use:
uvicorn src.main:app --port 8001

# Frontend - Vite will automatically find next available port
npm run dev
```

## Development Workflow

### Backend Development
```bash
cd backend
source venv/bin/activate
python3 src/main.py
```

### Frontend Development
```bash
cd frontend
npm run dev
```

### Building for Production
```bash
# Frontend
cd frontend
npm run build

# Backend
cd backend
# Production deployment with gunicorn or similar ASGI server
```

## Project Structure

```
ia-homelab/
├── backend/                 # FastAPI Python backend
│   ├── src/
│   │   ├── main.py         # Application entry point
│   │   ├── models/         # Database models
│   │   ├── routers/        # API endpoints
│   │   ├── services/       # Business logic
│   │   ├── websocket/      # WebSocket handlers
│   │   └── database/       # Database configuration
│   ├── requirements.txt    # Python dependencies
│   └── .env               # Environment variables
├── frontend/               # React TypeScript frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── hooks/          # Custom React hooks
│   │   ├── lib/           # Utilities and API client
│   │   └── types/         # TypeScript definitions
│   ├── package.json       # Node.js dependencies
│   └── tailwind.config.js # Tailwind CSS configuration
└── INSTALLATION.md        # This file
```

## Next Steps

After successful installation:

1. **Configure Services**: Add your homelab service connections in the backend configuration
2. **Set Up Monitoring**: Configure system monitoring and alerting
3. **Customize UI**: Modify the frontend components to match your needs
4. **Deploy**: Follow production deployment guidelines for your environment

## Support

If you encounter issues during installation:

1. Check the troubleshooting section above
2. Ensure all prerequisites are met
3. Verify environment configurations
4. Check service logs for detailed error messages

The application follows a microservices architecture with clear separation between frontend and backend, making it easy to develop and deploy independently.