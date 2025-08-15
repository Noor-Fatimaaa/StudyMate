from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import tempfile
import os
from pathlib import Path
import logging

from app.database import get_db
from models.database import Project, Document, ChatMessage
from services.document_service import DocumentService
from services.chat_service import ChatService
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize services
document_service = DocumentService()
chat_service = ChatService()

# Create router
router = APIRouter()


# Pydantic models for request/response
from pydantic import BaseModel

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: str
    updated_at: Optional[str]
    
    class Config:
        from_attributes = True

class DocumentResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    content_preview: Optional[str]
    page_count: Optional[int]
    processing_status: str
    error_message: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    message: str
    model_type: Optional[str] = None
    stream: bool = False

class ChatResponse(BaseModel):
    answer: str
    citations: List[dict]
    related_excerpts: List[str]
    model_used: str
    tokens_used: int
    response_time: int

class ChatHistoryResponse(BaseModel):
    id: int
    message: str
    response: str
    citations: Optional[List[dict]]
    related_excerpts: Optional[List[str]]
    model_used: str
    tokens_used: Optional[int]
    response_time: Optional[int]
    created_at: str
    
    class Config:
        from_attributes = True


# Project endpoints
@router.post("/projects", response_model=ProjectResponse)
async def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project"""
    try:
        db_project = Project(
            name=project.name,
            description=project.description
        )
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        
        return ProjectResponse(
            id=db_project.id,
            name=db_project.name,
            description=db_project.description,
            created_at=db_project.created_at.isoformat(),
            updated_at=db_project.updated_at.isoformat() if db_project.updated_at else None
        )
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail="Failed to create project")


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(db: Session = Depends(get_db)):
    """List all projects"""
    try:
        projects = db.query(Project).order_by(Project.created_at.desc()).all()
        return [
            ProjectResponse(
                id=p.id,
                name=p.name,
                description=p.description,
                created_at=p.created_at.isoformat(),
                updated_at=p.updated_at.isoformat() if p.updated_at else None
            )
            for p in projects
        ]
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail="Failed to list projects")


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get a specific project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat() if project.updated_at else None
    )


@router.delete("/projects/{project_id}")
async def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Delete a project and all its documents"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Delete all documents in the project
        documents = document_service.get_project_documents(project_id, db)
        for doc in documents:
            await document_service.delete_document(doc.id, db)
        
        # Delete the project
        db.delete(project)
        db.commit()
        
        return {"message": "Project deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete project")


# Document endpoints
@router.post("/projects/{project_id}/upload")
async def upload_document(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a document to a project"""
    try:
        # Validate project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Validate file type
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in settings.allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"File type {file_extension} not supported. Allowed types: {settings.allowed_extensions}"
            )
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Process the document
            document = await document_service.upload_document(
                temp_file_path, file.filename, project_id, db
            )
            
            return {
                "message": "Document uploaded successfully",
                "document_id": document.id,
                "status": document.processing_status
            }
        finally:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload document")


@router.get("/projects/{project_id}/documents", response_model=List[DocumentResponse])
async def list_project_documents(project_id: int, db: Session = Depends(get_db)):
    """List all documents in a project"""
    try:
        # Validate project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        documents = document_service.get_project_documents(project_id, db)
        return [
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                original_filename=doc.original_filename,
                file_type=doc.file_type,
                file_size=doc.file_size,
                content_preview=doc.content_preview,
                page_count=doc.page_count,
                processing_status=doc.processing_status,
                error_message=doc.error_message,
                created_at=doc.created_at.isoformat()
            )
            for doc in documents
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to list documents")


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: int, db: Session = Depends(get_db)):
    """Get a specific document"""
    document = document_service.get_document(document_id, db)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        original_filename=document.original_filename,
        file_type=document.file_type,
        file_size=document.file_size,
        content_preview=document.content_preview,
        page_count=document.page_count,
        processing_status=document.processing_status,
        error_message=document.error_message,
        created_at=document.created_at.isoformat()
    )


@router.delete("/documents/{document_id}")
async def delete_document(document_id: int, db: Session = Depends(get_db)):
    """Delete a document"""
    try:
        success = await document_service.delete_document(document_id, db)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {"message": "Document deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")


# Chat endpoints
@router.post("/projects/{project_id}/chat")
async def chat_with_documents(
    project_id: int,
    chat_request: ChatRequest,
    db: Session = Depends(get_db)
):
    """Chat with documents in a project"""
    try:
        # Validate project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Validate message
        if not chat_request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        if chat_request.stream:
            # Return streaming response
            async def generate():
                async for chunk in chat_service.chat(
                    message=chat_request.message,
                    project_id=project_id,
                    model_type=chat_request.model_type,
                    stream=True,
                    db=db
                ):
                    yield chunk
            
            return StreamingResponse(
                generate(),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache"}
            )
        else:
            # Return complete response
            response = await chat_service.chat(
                message=chat_request.message,
                project_id=project_id,
                model_type=chat_request.model_type,
                stream=False,
                db=db
            )
            
            return ChatResponse(**response)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail="Failed to process chat request")


@router.get("/projects/{project_id}/chat/history", response_model=List[ChatHistoryResponse])
async def get_chat_history(
    project_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get chat history for a project"""
    try:
        # Validate project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        messages = chat_service.get_chat_history_full(project_id, db, limit)
        return [
            ChatHistoryResponse(
                id=msg.id,
                message=msg.message,
                response=msg.response,
                citations=msg.citations,
                related_excerpts=msg.related_excerpts,
                model_used=msg.model_used,
                tokens_used=msg.tokens_used,
                response_time=msg.response_time,
                created_at=msg.created_at.isoformat()
            )
            for msg in messages
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chat history")


@router.delete("/chat/{message_id}")
async def delete_chat_message(message_id: int, db: Session = Depends(get_db)):
    """Delete a chat message"""
    try:
        success = chat_service.delete_chat_message(message_id, db)
        if not success:
            raise HTTPException(status_code=404, detail="Chat message not found")
        
        return {"message": "Chat message deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chat message: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete chat message")


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "StudyMate API"}