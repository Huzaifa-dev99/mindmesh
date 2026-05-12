# MindMesh

AI-powered journaling and knowledge management platform that helps users capture thoughts, extract insights, and build personal knowledge graphs through intelligent analysis.

## Overview

MindMesh combines the introspective power of journaling with modern AI to create a comprehensive knowledge management system. Users can write journal entries, receive AI-powered insights, and build interconnected knowledge networks that evolve over time.

### Key Features (Planned)

- **Intelligent Journaling**: Write entries with AI-assisted content analysis and insight generation
- **Knowledge Graph**: Automatically build and navigate personal knowledge networks
- **Semantic Search**: Find relevant entries and insights using natural language queries
- **Privacy-First**: Local processing with optional cloud synchronization
- **Multi-Modal**: Support for text, images, and structured data

## Architecture

MindMesh follows a modern, scalable architecture designed for maintainability and extensibility:

### Backend (FastAPI)
- **API Layer**: RESTful endpoints with automatic OpenAPI documentation
- **Service Layer**: Business logic orchestration and domain rules
- **Repository Layer**: Data access abstraction with async database operations
- **AI Layer**: Integration with Groq API for intelligent processing
- **Vector DB**: Qdrant for semantic search and knowledge retrieval

### Frontend (Streamlit)
- **Pages**: Modular page-based navigation
- **Components**: Reusable UI components
- **Services**: API client for backend communication
- **State**: Session management and application state

### Data Layer
- **PostgreSQL**: Relational data storage
- **Qdrant**: Vector database for embeddings and similarity search

## Tech Stack

### Backend
- **Framework**: FastAPI (async Python web framework)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Vector DB**: Qdrant for semantic search
- **AI**: Groq API for language model integration
- **Migration**: Alembic for database schema management

### Frontend
- **Framework**: Streamlit for rapid web app development
- **API Client**: HTTPX for backend communication

### Infrastructure
- **Containerization**: Docker with Docker Compose
- **Development**: Hot reload, volume mounting, service orchestration

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd mindmesh
   ```

2. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Start Development Environment**

   **Option A: Minimal Setup** (PostgreSQL & Qdrant running locally outside Docker)
   ```bash
   docker-compose up --build
   ```

   **Option B: Local Containers** (PostgreSQL & Qdrant in Docker)
   ```bash
   docker-compose -f docker-compose.local.yml up --build
   ```

   **Option C: Complete Setup** (All services in Docker, production-ready)
   ```bash
   docker-compose -f docker-compose.full.yml up --build
   ```

4. **Access the Application**
   - Frontend: http://localhost:8501
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Development Workflow

1. **Backend Development**
   ```bash
   cd backend
   pip install -e .
   uvicorn app.main:app --reload
   ```

2. **Frontend Development**
   ```bash
   cd frontend
   pip install -r requirements.txt
   streamlit run app/main.py
   ```

## Project Structure

```
mindmesh/
├── backend/                 # FastAPI backend application
│   ├── app/
│   │   ├── ai/             # AI service integrations
│   │   ├── api/            # API routing and endpoints
│   │   ├── core/           # Configuration and settings
│   │   ├── db/             # Database connections and models
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── repositories/   # Data access layer
│   │   ├── schemas/        # Pydantic validation schemas
│   │   └── services/       # Business logic layer
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/                # Streamlit frontend application
│   ├── app/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Application pages
│   │   ├── services/       # API client services
│   │   ├── state/          # State management
│   │   └── utils/          # Frontend utilities
│   ├── Dockerfile
│   └── requirements.txt
├── docker/                  # Docker-related files
├── docs/                    # Documentation
├── scripts/                 # Automation scripts
├── docker-compose.yml       # Development environment
├── .env.example            # Environment template
└── .gitignore              # Git ignore patterns
```

## Development Status

### Implemented ✅
- Project structure and scaffolding
- Docker containerization setup
- Basic API routing framework
- Database and AI service foundations
- Environment configuration management

### In Progress 🚧
- Core business logic implementation
- AI integration and processing pipelines
- User authentication and authorization
- Frontend UI development

### Planned 📋
- Knowledge graph visualization
- Advanced search capabilities
- Multi-user collaboration features
- Mobile application
- Plugin system for extensibility

## Contributing

See [docs/development.md](docs/development.md) for detailed development guidelines and contribution process.

## License

[License information to be added]

## Roadmap

### Phase 1: Foundation (Current)
- [x] Project structure and architecture
- [x] Development environment setup
- [ ] Basic user authentication
- [ ] Journal entry CRUD operations

### Phase 2: AI Integration
- [ ] AI-powered content analysis
- [ ] Knowledge extraction and tagging
- [ ] Semantic search implementation
- [ ] Insight generation

### Phase 3: Advanced Features
- [ ] Knowledge graph visualization
- [ ] Collaborative features
- [ ] Advanced analytics
- [ ] Mobile application

### Phase 4: Ecosystem
- [ ] Plugin system
- [ ] API ecosystem
- [ ] Integration with external tools
- [ ] Enterprise features