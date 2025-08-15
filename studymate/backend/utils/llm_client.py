from typing import List, Dict, Any, Optional, AsyncGenerator
import logging
from app.config import settings
import asyncio
import json
import httpx
from datetime import datetime

# LLM Client imports
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage

logger = logging.getLogger(__name__)


class LLMClient:
    """Abstract base class for LLM clients"""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.max_tokens = settings.max_context_tokens
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        stream: bool = False
    ) -> Dict[str, Any]:
        """Generate response from LLM"""
        raise NotImplementedError
    
    async def stream_response(
        self, 
        messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """Stream response from LLM"""
        raise NotImplementedError


class OpenAIClient(LLMClient):
    """OpenAI GPT client"""
    
    def __init__(self):
        super().__init__(settings.openai_model)
        self.client = ChatOpenAI(
            openai_api_key=settings.openai_api_key,
            model=settings.openai_model,
            temperature=0.1,
            streaming=True
        )
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        stream: bool = False
    ) -> Dict[str, Any]:
        """Generate response from OpenAI"""
        try:
            start_time = datetime.now()
            
            # Convert messages to LangChain format
            langchain_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    langchain_messages.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_messages.append(AIMessage(content=msg["content"]))
            
            if stream:
                return await self.stream_response(messages)
            
            response = await self.client.agenerate([langchain_messages])
            
            end_time = datetime.now()
            response_time = int((end_time - start_time).total_seconds() * 1000)
            
            return {
                "content": response.generations[0][0].text,
                "model": self.model_name,
                "tokens_used": response.llm_output.get("token_usage", {}).get("total_tokens", 0),
                "response_time": response_time
            }
            
        except Exception as e:
            logger.error(f"Error generating OpenAI response: {e}")
            raise
    
    async def stream_response(
        self, 
        messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """Stream response from OpenAI"""
        try:
            # Convert messages to LangChain format
            langchain_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    langchain_messages.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_messages.append(AIMessage(content=msg["content"]))
            
            async for chunk in self.client.astream(langchain_messages):
                if chunk.content:
                    yield chunk.content
                    
        except Exception as e:
            logger.error(f"Error streaming OpenAI response: {e}")
            yield f"Error: {str(e)}"


class ClaudeClient(LLMClient):
    """Anthropic Claude client"""
    
    def __init__(self):
        super().__init__(settings.claude_model)
        self.client = ChatAnthropic(
            anthropic_api_key=settings.claude_api_key,
            model=settings.claude_model,
            temperature=0.1,
            streaming=True
        )
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        stream: bool = False
    ) -> Dict[str, Any]:
        """Generate response from Claude"""
        try:
            start_time = datetime.now()
            
            # Convert messages to LangChain format
            langchain_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    langchain_messages.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_messages.append(AIMessage(content=msg["content"]))
            
            if stream:
                return await self.stream_response(messages)
            
            response = await self.client.agenerate([langchain_messages])
            
            end_time = datetime.now()
            response_time = int((end_time - start_time).total_seconds() * 1000)
            
            return {
                "content": response.generations[0][0].text,
                "model": self.model_name,
                "tokens_used": response.llm_output.get("token_usage", {}).get("total_tokens", 0),
                "response_time": response_time
            }
            
        except Exception as e:
            logger.error(f"Error generating Claude response: {e}")
            raise
    
    async def stream_response(
        self, 
        messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """Stream response from Claude"""
        try:
            # Convert messages to LangChain format
            langchain_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    langchain_messages.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_messages.append(AIMessage(content=msg["content"]))
            
            async for chunk in self.client.astream(langchain_messages):
                if chunk.content:
                    yield chunk.content
                    
        except Exception as e:
            logger.error(f"Error streaming Claude response: {e}")
            yield f"Error: {str(e)}"


class GeminiClient(LLMClient):
    """Google Gemini client"""
    
    def __init__(self):
        super().__init__(settings.gemini_model)
        self.client = ChatGoogleGenerativeAI(
            google_api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            temperature=0.1,
            streaming=True
        )
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        stream: bool = False
    ) -> Dict[str, Any]:
        """Generate response from Gemini"""
        try:
            start_time = datetime.now()
            
            # Convert messages to LangChain format
            langchain_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    langchain_messages.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_messages.append(AIMessage(content=msg["content"]))
            
            if stream:
                return await self.stream_response(messages)
            
            response = await self.client.agenerate([langchain_messages])
            
            end_time = datetime.now()
            response_time = int((end_time - start_time).total_seconds() * 1000)
            
            return {
                "content": response.generations[0][0].text,
                "model": self.model_name,
                "tokens_used": response.llm_output.get("token_usage", {}).get("total_tokens", 0),
                "response_time": response_time
            }
            
        except Exception as e:
            logger.error(f"Error generating Gemini response: {e}")
            raise
    
    async def stream_response(
        self, 
        messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """Stream response from Gemini"""
        try:
            # Convert messages to LangChain format
            langchain_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    langchain_messages.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_messages.append(AIMessage(content=msg["content"]))
            
            async for chunk in self.client.astream(langchain_messages):
                if chunk.content:
                    yield chunk.content
                    
        except Exception as e:
            logger.error(f"Error streaming Gemini response: {e}")
            yield f"Error: {str(e)}"


class LocalLLMClient(LLMClient):
    """Local LLM client (Ollama)"""
    
    def __init__(self):
        super().__init__(settings.local_llm_model)
        self.base_url = settings.local_llm_url
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        stream: bool = False
    ) -> Dict[str, Any]:
        """Generate response from local LLM"""
        try:
            start_time = datetime.now()
            
            if stream:
                return await self.stream_response(messages)
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "stream": False
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                end_time = datetime.now()
                response_time = int((end_time - start_time).total_seconds() * 1000)
                
                return {
                    "content": result["message"]["content"],
                    "model": self.model_name,
                    "tokens_used": result.get("eval_count", 0) + result.get("prompt_eval_count", 0),
                    "response_time": response_time
                }
                
        except Exception as e:
            logger.error(f"Error generating local LLM response: {e}")
            raise
    
    async def stream_response(
        self, 
        messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """Stream response from local LLM"""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "stream": True
                    }
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                data = json.loads(line)
                                if "message" in data and "content" in data["message"]:
                                    yield data["message"]["content"]
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            logger.error(f"Error streaming local LLM response: {e}")
            yield f"Error: {str(e)}"


def get_llm_client(model_type: Optional[str] = None) -> LLMClient:
    """Factory function to get the configured LLM client"""
    model_type = model_type or settings.default_llm
    
    if model_type == "openai":
        return OpenAIClient()
    elif model_type == "claude":
        return ClaudeClient()
    elif model_type == "gemini":
        return GeminiClient()
    elif model_type == "local":
        return LocalLLMClient()
    else:
        raise ValueError(f"Unsupported model type: {model_type}")


def create_rag_prompt(query: str, context_chunks: List[Dict[str, Any]], chat_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Create a RAG prompt with context and chat history"""
    
    # Build context from chunks
    context_text = ""
    citations = []
    
    for i, chunk in enumerate(context_chunks):
        context_text += f"\n\n[Document {i+1}: {chunk['filename']}]"
        if chunk.get('page_number'):
            context_text += f" (Page {chunk['page_number']})"
        if chunk.get('section_title'):
            context_text += f" - {chunk['section_title']}"
        context_text += f"\n{chunk['content']}"
        
        citations.append({
            "file": chunk['filename'],
            "page": chunk.get('page_number'),
            "section": chunk.get('section_title')
        })
    
    # System prompt
    system_prompt = """You are StudyMate, an AI assistant that helps users understand and analyze their documents. You have access to specific document content and should provide accurate, helpful responses based on that content.

Instructions:
1. Answer questions using ONLY the provided document context
2. If the answer isn't in the documents, say "I don't have enough information in the uploaded documents to answer this question"
3. Always cite your sources by mentioning the document name and page/section when applicable
4. Provide specific quotes when relevant
5. Suggest related topics or sections that might be of interest
6. Be conversational but accurate
7. If asked about something not in the documents, politely redirect to the available content

Context from uploaded documents:""" + context_text
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add chat history (last 5 exchanges to stay within token limits)
    if chat_history:
        for msg in chat_history[-10:]:  # Last 5 exchanges (user + assistant)
            messages.append(msg)
    
    # Add current query
    messages.append({"role": "user", "content": query})
    
    return messages