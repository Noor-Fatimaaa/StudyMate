from typing import List, Dict, Any, Optional
import os
import uuid
import asyncio
from pathlib import Path
import logging
from sqlalchemy.orm import Session
import boto3
from botocore.exceptions import ClientError
import aiofiles

from app.config import settings
from models.database import Document, DocumentChunk, Project
from utils.document_processor import DocumentProcessor
from utils.vector_store import get_vector_store
from app.database import get_redis

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for handling document operations"""
    
    def __init__(self):
        self.processor = DocumentProcessor()
        self.vector_store = get_vector_store()
        self.redis_client = get_redis()
        
        # Initialize S3 client if configured
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region
            )
        else:
            self.s3_client = None
    
    async def upload_document(
        self, 
        file_path: str, 
        filename: str, 
        project_id: int, 
        db: Session
    ) -> Document:
        """
        Upload and process a document
        
        Args:
            file_path: Path to the uploaded file
            filename: Original filename
            project_id: ID of the project to add document to
            db: Database session
            
        Returns:
            Document model instance
        """
        try:
            # Validate file
            file_size = os.path.getsize(file_path)
            file_extension = Path(filename).suffix.lower()
            
            if file_extension not in settings.allowed_extensions:
                raise ValueError(f"File type {file_extension} not supported")
            
            if file_size > settings.max_file_size:
                raise ValueError(f"File size {file_size} exceeds limit")
            
            # Create document record
            unique_filename = f"{uuid.uuid4()}_{filename}"
            document = Document(
                filename=unique_filename,
                original_filename=filename,
                file_type=file_extension,
                file_size=file_size,
                project_id=project_id,
                processing_status="pending"
            )
            
            db.add(document)
            db.commit()
            db.refresh(document)
            
            # Upload to S3 if configured
            s3_key = None
            if self.s3_client and settings.aws_s3_bucket:
                try:
                    s3_key = f"documents/{project_id}/{unique_filename}"
                    self.s3_client.upload_file(file_path, settings.aws_s3_bucket, s3_key)
                    document.s3_key = s3_key
                    logger.info(f"Uploaded {filename} to S3: {s3_key}")
                except ClientError as e:
                    logger.error(f"Failed to upload to S3: {e}")
            
            # Process document asynchronously
            asyncio.create_task(self._process_document_async(document.id, file_path, filename, db))
            
            return document
            
        except Exception as e:
            logger.error(f"Error uploading document {filename}: {e}")
            if 'document' in locals():
                document.processing_status = "failed"
                document.error_message = str(e)
                db.commit()
            raise
    
    async def _process_document_async(
        self, 
        document_id: int, 
        file_path: str, 
        filename: str, 
        db: Session
    ):
        """Process document asynchronously"""
        try:
            # Update status
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return
            
            document.processing_status = "processing"
            db.commit()
            
            # Process document
            processed_data = self.processor.process_document(file_path, filename)
            
            # Update document with processed data
            document.content_preview = processed_data['full_text'][:500]
            document.page_count = processed_data.get('page_count', 1)
            
            # Create document chunks
            chunks_data = []
            for chunk in processed_data['chunks']:
                chunk_record = DocumentChunk(
                    content=chunk['content'],
                    page_number=chunk.get('page_number'),
                    section_title=chunk.get('section_title'),
                    chunk_index=chunk['chunk_index'],
                    metadata=chunk.get('metadata', {}),
                    document_id=document_id
                )
                db.add(chunk_record)
                
                # Prepare for vector storage
                chunks_data.append({
                    'content': chunk['content'],
                    'document_id': document_id,
                    'filename': filename,
                    'chunk_index': chunk['chunk_index'],
                    'page_number': chunk.get('page_number'),
                    'section_title': chunk.get('section_title'),
                    'metadata': chunk.get('metadata', {})
                })
            
            db.commit()
            
            # Store in vector database
            vector_ids = self.vector_store.add_documents(chunks_data, document.project_id)
            
            # Update chunks with vector IDs
            chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
            for i, chunk in enumerate(chunks):
                if i < len(vector_ids):
                    chunk.vector_id = vector_ids[i]
            
            # Mark as completed
            document.processing_status = "completed"
            db.commit()
            
            logger.info(f"Successfully processed document {filename}")
            
        except Exception as e:
            logger.error(f"Error processing document {filename}: {e}")
            document.processing_status = "failed"
            document.error_message = str(e)
            db.commit()
    
    def get_project_documents(self, project_id: int, db: Session) -> List[Document]:
        """Get all documents for a project"""
        return db.query(Document).filter(Document.project_id == project_id).all()
    
    def get_document(self, document_id: int, db: Session) -> Optional[Document]:
        """Get a specific document"""
        return db.query(Document).filter(Document.id == document_id).first()
    
    async def delete_document(self, document_id: int, db: Session) -> bool:
        """Delete a document and its chunks"""
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return False
            
            # Get vector IDs for deletion
            chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
            vector_ids = [chunk.vector_id for chunk in chunks if chunk.vector_id]
            
            # Delete from vector store
            if vector_ids:
                self.vector_store.delete_documents(vector_ids)
            
            # Delete from S3
            if document.s3_key and self.s3_client:
                try:
                    self.s3_client.delete_object(
                        Bucket=settings.aws_s3_bucket, 
                        Key=document.s3_key
                    )
                except ClientError as e:
                    logger.error(f"Failed to delete from S3: {e}")
            
            # Delete from database (cascades to chunks)
            db.delete(document)
            db.commit()
            
            logger.info(f"Deleted document {document.original_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return False
    
    def search_documents(
        self, 
        query: str, 
        project_id: int, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for relevant document chunks"""
        try:
            results = self.vector_store.search(query, project_id, k=limit)
            return results
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []