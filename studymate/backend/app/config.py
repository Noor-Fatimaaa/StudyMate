from pydantic_settings import BaseSettings
from typing import Optional, Literal
import os


class Settings(BaseSettings):
    # API Configuration
    app_name: str = "StudyMate API"
    debug: bool = False
    api_v1_str: str = "/api/v1"
    
    # Database
    postgres_uri: str
    redis_url: str = "redis://localhost:6379"
    
    # Vector Database
    vector_db_type: Literal["weaviate", "chromadb"] = "weaviate"
    weaviate_url: Optional[str] = None
    weaviate_api_key: Optional[str] = None
    chromadb_persist_directory: str = "./chromadb"
    
    # LLM Configuration
    default_llm: Literal["claude", "openai", "gemini", "local"] = "claude"
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    
    # Anthropic Claude
    claude_api_key: Optional[str] = None
    claude_model: str = "claude-3-5-sonnet-20241022"
    
    # Google Gemini
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-pro"
    
    # Local LLM (Ollama)
    local_llm_url: str = "http://localhost:11434"
    local_llm_model: str = "llama3.1:8b"
    
    # Embeddings
    embedding_model: Literal["openai", "local"] = "openai"
    openai_embedding_model: str = "text-embedding-3-large"
    local_embedding_model: str = "all-mpnet-base-v2"
    
    # File Storage
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_s3_bucket: Optional[str] = None
    aws_region: str = "us-east-1"
    
    # File Upload Limits
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_extensions: list[str] = [".pdf", ".docx", ".txt", ".html"]
    
    # RAG Configuration
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_context_tokens: int = 200000  # For long-context models
    retrieval_k: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()