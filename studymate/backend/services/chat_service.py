from typing import List, Dict, Any, Optional, AsyncGenerator
import logging
from sqlalchemy.orm import Session
from datetime import datetime
import json
import re

from app.config import settings
from models.database import ChatMessage, Project
from services.document_service import DocumentService
from utils.llm_client import get_llm_client, create_rag_prompt
from app.database import get_redis

logger = logging.getLogger(__name__)


class ChatService:
    """Service for handling chat operations with RAG"""
    
    def __init__(self):
        self.document_service = DocumentService()
        self.redis_client = get_redis()
    
    async def chat(
        self,
        message: str,
        project_id: int,
        model_type: Optional[str] = None,
        stream: bool = False,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Generate chat response using RAG
        
        Args:
            message: User's message/question
            project_id: ID of the project for context
            model_type: LLM model to use (optional, uses default if None)
            stream: Whether to stream the response
            db: Database session
            
        Returns:
            Dict with response, citations, and related excerpts
        """
        try:
            # Validate input
            if not message.strip():
                raise ValueError("Message cannot be empty")
            
            # Check if project exists
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise ValueError("Project not found")
            
            # Get chat history
            chat_history = self._get_chat_history(project_id, db)
            
            # Search for relevant documents
            relevant_chunks = self.document_service.search_documents(
                message, 
                project_id, 
                limit=settings.retrieval_k
            )
            
            if not relevant_chunks:
                return {
                    "answer": "No relevant information found in uploaded documents. Please upload documents related to your question.",
                    "citations": [],
                    "related_excerpts": [],
                    "model_used": model_type or settings.default_llm,
                    "tokens_used": 0,
                    "response_time": 0
                }
            
            # Create RAG prompt
            messages = create_rag_prompt(message, relevant_chunks, chat_history)
            
            # Get LLM client
            llm_client = get_llm_client(model_type)
            
            if stream:
                return await self._stream_chat_response(
                    messages, llm_client, message, project_id, relevant_chunks, db
                )
            else:
                return await self._generate_chat_response(
                    messages, llm_client, message, project_id, relevant_chunks, db
                )
                
        except Exception as e:
            logger.error(f"Error in chat service: {e}")
            raise
    
    async def _generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        llm_client,
        original_message: str,
        project_id: int,
        relevant_chunks: List[Dict[str, Any]],
        db: Session
    ) -> Dict[str, Any]:
        """Generate a complete chat response"""
        start_time = datetime.now()
        
        # Generate response
        response_data = await llm_client.generate_response(messages)
        
        # Extract citations and related excerpts
        citations = self._extract_citations(response_data["content"], relevant_chunks)
        related_excerpts = self._get_related_excerpts(relevant_chunks, response_data["content"])
        
        # Save to database
        chat_message = ChatMessage(
            message=original_message,
            response=response_data["content"],
            citations=citations,
            related_excerpts=related_excerpts,
            model_used=response_data["model"],
            tokens_used=response_data.get("tokens_used", 0),
            response_time=response_data.get("response_time", 0),
            project_id=project_id
        )
        
        db.add(chat_message)
        db.commit()
        
        return {
            "answer": response_data["content"],
            "citations": citations,
            "related_excerpts": related_excerpts,
            "model_used": response_data["model"],
            "tokens_used": response_data.get("tokens_used", 0),
            "response_time": response_data.get("response_time", 0)
        }
    
    async def _stream_chat_response(
        self,
        messages: List[Dict[str, str]],
        llm_client,
        original_message: str,
        project_id: int,
        relevant_chunks: List[Dict[str, Any]],
        db: Session
    ) -> AsyncGenerator[str, None]:
        """Stream chat response"""
        full_response = ""
        start_time = datetime.now()
        
        try:
            async for chunk in llm_client.stream_response(messages):
                full_response += chunk
                yield json.dumps({"type": "content", "data": chunk}) + "\n"
            
            # Extract citations and related excerpts
            citations = self._extract_citations(full_response, relevant_chunks)
            related_excerpts = self._get_related_excerpts(relevant_chunks, full_response)
            
            # Send citations
            yield json.dumps({"type": "citations", "data": citations}) + "\n"
            
            # Send related excerpts
            yield json.dumps({"type": "related_excerpts", "data": related_excerpts}) + "\n"
            
            # Calculate response time
            end_time = datetime.now()
            response_time = int((end_time - start_time).total_seconds() * 1000)
            
            # Save to database
            chat_message = ChatMessage(
                message=original_message,
                response=full_response,
                citations=citations,
                related_excerpts=related_excerpts,
                model_used=llm_client.model_name,
                tokens_used=0,  # Token counting for streaming is complex
                response_time=response_time,
                project_id=project_id
            )
            
            db.add(chat_message)
            db.commit()
            
            # Send completion signal
            yield json.dumps({"type": "done", "data": {"response_time": response_time}}) + "\n"
            
        except Exception as e:
            logger.error(f"Error streaming response: {e}")
            yield json.dumps({"type": "error", "data": str(e)}) + "\n"
    
    def _get_chat_history(self, project_id: int, db: Session, limit: int = 10) -> List[Dict[str, str]]:
        """Get recent chat history for context"""
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.project_id == project_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        
        history = []
        for msg in reversed(messages):  # Reverse to get chronological order
            history.append({"role": "user", "content": msg.message})
            history.append({"role": "assistant", "content": msg.response})
        
        return history
    
    def _extract_citations(self, response: str, relevant_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract citations from response based on relevant chunks"""
        citations = []
        seen_citations = set()
        
        for chunk in relevant_chunks:
            filename = chunk.get('filename', '')
            page_number = chunk.get('page_number')
            section_title = chunk.get('section_title')
            
            # Check if the chunk content is referenced in the response
            # This is a simple heuristic - could be improved with more sophisticated matching
            chunk_words = set(chunk['content'].lower().split())
            response_words = set(response.lower().split())
            
            # If there's significant overlap, consider it a citation
            overlap = len(chunk_words.intersection(response_words))
            if overlap > 5:  # Threshold for considering it a citation
                citation_key = f"{filename}_{page_number}_{section_title}"
                if citation_key not in seen_citations:
                    citation = {
                        "file": filename,
                        "page": page_number,
                        "section": section_title
                    }
                    citations.append(citation)
                    seen_citations.add(citation_key)
        
        return citations[:3]  # Limit to top 3 citations
    
    def _get_related_excerpts(self, relevant_chunks: List[Dict[str, Any]], response: str) -> List[str]:
        """Get related excerpts for deeper reading"""
        excerpts = []
        
        # Get chunks that weren't heavily used in the response
        for chunk in relevant_chunks:
            chunk_content = chunk['content']
            
            # Simple heuristic: if less than 30% of chunk words appear in response,
            # it might be a good related excerpt
            chunk_words = set(chunk_content.lower().split())
            response_words = set(response.lower().split())
            overlap_ratio = len(chunk_words.intersection(response_words)) / len(chunk_words)
            
            if overlap_ratio < 0.3 and len(chunk_content) > 100:
                # Truncate to a reasonable length
                excerpt = chunk_content[:300]
                if len(chunk_content) > 300:
                    excerpt += "..."
                excerpts.append(excerpt)
        
        return excerpts[:3]  # Limit to 3 related excerpts
    
    def get_chat_history_full(self, project_id: int, db: Session, limit: int = 50) -> List[ChatMessage]:
        """Get full chat history for a project"""
        return (
            db.query(ChatMessage)
            .filter(ChatMessage.project_id == project_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )
    
    def delete_chat_message(self, message_id: int, db: Session) -> bool:
        """Delete a chat message"""
        try:
            message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
            if message:
                db.delete(message)
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting chat message: {e}")
            return False