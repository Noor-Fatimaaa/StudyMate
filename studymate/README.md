# StudyMate 📚

> An AI-powered, document-grounded assistant inspired by Google's NotebookLM

StudyMate is a production-ready, full-stack application that allows users to upload documents (PDFs, DOCX, TXT, HTML) and chat with them using advanced AI models. Get precise, citation-rich answers grounded in your uploaded content.

## ✨ Features

### 📄 Multi-Document Support
- **File Types**: PDF, DOCX, TXT, HTML
- **Smart Processing**: Semantic chunking with metadata preservation
- **Vector Storage**: Weaviate Cloud or ChromaDB for fast retrieval
- **Cloud Storage**: AWS S3 integration for document persistence

### 🤖 NotebookLM-Style Chat
- **Grounded Responses**: All answers sourced from your documents
- **Exact Citations**: File name + page/section references
- **Related Excerpts**: 2-3 suggested readings for deeper exploration
- **Chat Memory**: Contextual conversations within each project

### 🧠 Multi-Model AI Support
- **Claude 3.5 Sonnet** (default) - Best for analysis and reasoning
- **GPT-4o** - Excellent general-purpose performance
- **Gemini 1.5 Pro** - Long-context understanding (200k tokens)
- **Local LLaMA** - Privacy-focused offline option (via Ollama)

### 🎨 Modern UI/UX
- **Next.js 14** with App Router
- **shadcn/ui** components with Tailwind CSS
- **Real-time Streaming** responses
- **Framer Motion** animations
- **Dark/Light Mode** support

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   Vector DB     │
│   (Next.js 14)  │◄──►│   (FastAPI)     │◄──►│ (Weaviate/      │
│                 │    │                 │    │  ChromaDB)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Browser  │    │   PostgreSQL    │    │   AWS S3        │
│                 │    │   (Metadata)    │    │   (Files)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.12+ (for local development)
- API keys for your preferred LLM provider

### 1. Clone & Setup

```bash
git clone <repository-url>
cd studymate

# Copy environment variables
cp .env.example .env

# Edit .env with your API keys
nano .env
```

### 2. Configure Environment

Edit `.env` with your API keys:

```bash
# Required: At least one LLM API key
CLAUDE_API_KEY=your_claude_api_key
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key

# Optional: AWS S3 for file storage
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_S3_BUCKET=your_s3_bucket_name

# Optional: Weaviate Cloud
WEAVIATE_URL=https://your-cluster.weaviate.network
WEAVIATE_API_KEY=your_weaviate_api_key
```

### 3. Launch with Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check health
curl http://localhost:8000/health
curl http://localhost:3000
```

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (in debug mode)

## 📖 Usage Guide

### Creating Your First Project

1. **Create Project**: Click "New Project" and give it a name
2. **Upload Documents**: Drag & drop or click to upload PDFs, DOCX, TXT, or HTML files
3. **Wait for Processing**: Documents are parsed and indexed automatically
4. **Start Chatting**: Ask questions about your uploaded content

### Example Conversations

```
You: "What are the main findings in the research paper?"

StudyMate: "Based on the uploaded research paper 'AI_Study.pdf', 
the main findings include:

1. **Improved Accuracy**: The proposed model achieved 94.2% 
   accuracy on the benchmark dataset (Page 12, Results section)

2. **Reduced Training Time**: Training time was decreased by 
   40% compared to baseline methods (Page 15, Performance Analysis)

3. **Generalization**: The model showed strong performance 
   across multiple domains (Page 18, Discussion)

**Citations:**
- AI_Study.pdf, Page 12 (Results)
- AI_Study.pdf, Page 15 (Performance Analysis)

**Related Excerpts:**
- "The architecture modifications led to significant improvements..."
- "Cross-domain validation revealed consistent performance..."
- "Future work could explore hybrid approaches..."
```

## 🛠️ Development Setup

### Backend Development

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export POSTGRES_URI="postgresql://user:pass@localhost:5432/studymate"
export CLAUDE_API_KEY="your_key_here"

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Set environment variables
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Run development server
npm run dev
```

## 🚢 Production Deployment

### Railway (Recommended for Backend)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### Vercel (Recommended for Frontend)

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
cd frontend
vercel --prod
```

### AWS ECS / Docker

```bash
# Build and push images
docker build -t studymate-backend ./backend
docker build -t studymate-frontend ./frontend

# Push to ECR/DockerHub
docker tag studymate-backend your-registry/studymate-backend
docker push your-registry/studymate-backend
```

## 🔧 Configuration

### LLM Models

Configure your preferred models in `.env`:

```bash
# Default model for new chats
DEFAULT_LLM=claude  # claude, openai, gemini, local

# Model-specific settings
CLAUDE_MODEL=claude-3-5-sonnet-20241022
OPENAI_MODEL=gpt-4o
GEMINI_MODEL=gemini-1.5-pro
LOCAL_LLM_MODEL=llama3.1:8b
```

### Vector Database

Choose between Weaviate Cloud (managed) or ChromaDB (self-hosted):

```bash
# Weaviate Cloud (recommended for production)
VECTOR_DB_TYPE=weaviate
WEAVIATE_URL=https://your-cluster.weaviate.network
WEAVIATE_API_KEY=your_api_key

# ChromaDB (good for development)
VECTOR_DB_TYPE=chromadb
CHROMADB_PERSIST_DIRECTORY=./chromadb
```

### File Processing

Adjust chunking and processing settings:

```bash
CHUNK_SIZE=1000          # Characters per chunk
CHUNK_OVERLAP=200        # Overlap between chunks
MAX_FILE_SIZE=52428800   # 50MB max file size
RETRIEVAL_K=5            # Number of chunks to retrieve
```

## 📊 Monitoring & Observability

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Database connectivity
curl http://localhost:8000/api/v1/health

# Frontend health
curl http://localhost:3000/api/health
```

### Logs

```bash
# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### Metrics

Monitor key metrics:
- Document processing time
- Chat response latency
- Vector search performance
- Token usage by model
- Error rates

## 🔒 Security

### API Security

- Input validation on all endpoints
- File type and size restrictions
- SQL injection prevention
- XSS protection

### Data Privacy

- Documents stored securely (S3 + encryption)
- Vector embeddings isolated by project
- Chat history scoped to projects
- Optional local LLM for sensitive data

### Production Hardening

```bash
# Disable debug mode
DEBUG=false

# Use specific CORS origins
CORS_ORIGINS=https://your-domain.com

# Enable HTTPS
USE_TLS=true
TLS_CERT_PATH=/path/to/cert.pem
TLS_KEY_PATH=/path/to/key.pem
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Use TypeScript for all frontend code
- Add tests for new features
- Update documentation
- Ensure Docker builds pass

## 📝 API Documentation

### Core Endpoints

```bash
# Projects
GET    /api/v1/projects              # List projects
POST   /api/v1/projects              # Create project
GET    /api/v1/projects/{id}         # Get project
DELETE /api/v1/projects/{id}         # Delete project

# Documents
GET    /api/v1/projects/{id}/documents    # List documents
POST   /api/v1/projects/{id}/upload       # Upload document
DELETE /api/v1/documents/{id}             # Delete document

# Chat
POST   /api/v1/projects/{id}/chat         # Send message
GET    /api/v1/projects/{id}/chat/history # Get chat history
```

### Example API Calls

```bash
# Create a project
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Research Papers", "description": "AI research collection"}'

# Upload a document
curl -X POST http://localhost:8000/api/v1/projects/1/upload \
  -F "file=@paper.pdf"

# Chat with documents
curl -X POST http://localhost:8000/api/v1/projects/1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the main conclusions?", "stream": false}'
```

## 🐛 Troubleshooting

### Common Issues

**Backend won't start:**
```bash
# Check database connection
docker-compose logs postgres

# Verify environment variables
docker-compose exec backend env | grep -E "(POSTGRES|CLAUDE|OPENAI)"

# Reset database
docker-compose down -v
docker-compose up -d postgres
```

**Documents not processing:**
```bash
# Check vector database
docker-compose logs chromadb

# Verify file permissions
docker-compose exec backend ls -la /app/uploads

# Check processing logs
docker-compose logs backend | grep "processing"
```

**Frontend build errors:**
```bash
# Clear Next.js cache
rm -rf frontend/.next

# Reinstall dependencies
cd frontend && rm -rf node_modules && npm install

# Check environment variables
cat frontend/.env.local
```

### Performance Optimization

1. **Vector Database**: Use Weaviate Cloud for better performance
2. **Embeddings**: OpenAI embeddings are faster than local models
3. **Chunking**: Adjust `CHUNK_SIZE` based on document types
4. **Caching**: Redis caches frequently accessed data
5. **CDN**: Use Cloudflare for static assets

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by Google's NotebookLM
- Built with amazing open-source tools
- Special thanks to the AI/ML community

---

**Need Help?** Open an issue or check our [documentation wiki](wiki-link).

**Want to Contribute?** See our [contributing guidelines](CONTRIBUTING.md).

**Enterprise Support?** Contact us at [enterprise@studymate.ai](mailto:enterprise@studymate.ai).