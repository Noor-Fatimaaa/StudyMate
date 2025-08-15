import weaviate
import chromadb
from typing import List, Dict, Any, Optional, Tuple
import logging
from app.config import settings
from sentence_transformers import SentenceTransformer
from langchain_openai import OpenAIEmbeddings
import uuid

logger = logging.getLogger(__name__)


class VectorStore:
    """Abstract base class for vector storage operations"""
    
    def __init__(self):
        self.embeddings = self._initialize_embeddings()
    
    def _initialize_embeddings(self):
        """Initialize embedding model based on configuration"""
        if settings.embedding_model == "openai":
            return OpenAIEmbeddings(
                openai_api_key=settings.openai_api_key,
                model=settings.openai_embedding_model
            )
        else:
            return SentenceTransformer(settings.local_embedding_model)
    
    def add_documents(self, documents: List[Dict[str, Any]], project_id: int) -> List[str]:
        """Add documents to vector store"""
        raise NotImplementedError
    
    def search(self, query: str, project_id: int, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        raise NotImplementedError
    
    def delete_documents(self, document_ids: List[str]) -> bool:
        """Delete documents from vector store"""
        raise NotImplementedError


class WeaviateVectorStore(VectorStore):
    """Weaviate vector database implementation"""
    
    def __init__(self):
        super().__init__()
        self.client = weaviate.Client(
            url=settings.weaviate_url,
            auth_client_secret=weaviate.AuthApiKey(api_key=settings.weaviate_api_key) if settings.weaviate_api_key else None
        )
        self._ensure_schema()
    
    def _ensure_schema(self):
        """Ensure the required schema exists in Weaviate"""
        schema = {
            "classes": [{
                "class": "DocumentChunk",
                "description": "A chunk of text from a document",
                "properties": [
                    {
                        "name": "content",
                        "dataType": ["text"],
                        "description": "The text content of the chunk"
                    },
                    {
                        "name": "projectId",
                        "dataType": ["int"],
                        "description": "ID of the project this chunk belongs to"
                    },
                    {
                        "name": "documentId",
                        "dataType": ["int"],
                        "description": "ID of the document this chunk belongs to"
                    },
                    {
                        "name": "filename",
                        "dataType": ["string"],
                        "description": "Original filename"
                    },
                    {
                        "name": "chunkIndex",
                        "dataType": ["int"],
                        "description": "Index of this chunk within the document"
                    },
                    {
                        "name": "pageNumber",
                        "dataType": ["int"],
                        "description": "Page number (if applicable)"
                    },
                    {
                        "name": "sectionTitle",
                        "dataType": ["string"],
                        "description": "Section title (if applicable)"
                    },
                    {
                        "name": "metadata",
                        "dataType": ["string"],
                        "description": "Additional metadata as JSON string"
                    }
                ]
            }]
        }
        
        try:
            existing_schema = self.client.schema.get()
            if not any(cls["class"] == "DocumentChunk" for cls in existing_schema.get("classes", [])):
                self.client.schema.create(schema)
                logger.info("Created Weaviate schema")
        except Exception as e:
            logger.error(f"Error creating Weaviate schema: {e}")
    
    def add_documents(self, documents: List[Dict[str, Any]], project_id: int) -> List[str]:
        """Add documents to Weaviate"""
        vector_ids = []
        
        try:
            with self.client.batch as batch:
                batch.batch_size = 100
                
                for doc in documents:
                    # Generate embedding
                    if isinstance(self.embeddings, OpenAIEmbeddings):
                        embedding = self.embeddings.embed_query(doc['content'])
                    else:
                        embedding = self.embeddings.encode(doc['content']).tolist()
                    
                    vector_id = str(uuid.uuid4())
                    
                    properties = {
                        "content": doc['content'],
                        "projectId": project_id,
                        "documentId": doc.get('document_id'),
                        "filename": doc.get('filename', ''),
                        "chunkIndex": doc.get('chunk_index', 0),
                        "pageNumber": doc.get('page_number'),
                        "sectionTitle": doc.get('section_title', ''),
                        "metadata": str(doc.get('metadata', {}))
                    }
                    
                    batch.add_data_object(
                        properties,
                        "DocumentChunk",
                        uuid=vector_id,
                        vector=embedding
                    )
                    
                    vector_ids.append(vector_id)
            
            logger.info(f"Added {len(documents)} documents to Weaviate")
            return vector_ids
            
        except Exception as e:
            logger.error(f"Error adding documents to Weaviate: {e}")
            raise
    
    def search(self, query: str, project_id: int, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents in Weaviate"""
        try:
            # Generate query embedding
            if isinstance(self.embeddings, OpenAIEmbeddings):
                query_embedding = self.embeddings.embed_query(query)
            else:
                query_embedding = self.embeddings.encode(query).tolist()
            
            result = (
                self.client.query
                .get("DocumentChunk", [
                    "content", "filename", "chunkIndex", "pageNumber", 
                    "sectionTitle", "metadata", "documentId"
                ])
                .with_near_vector({"vector": query_embedding})
                .with_where({
                    "path": ["projectId"],
                    "operator": "Equal",
                    "valueInt": project_id
                })
                .with_limit(k)
                .with_additional(["distance"])
                .do()
            )
            
            documents = []
            for item in result["data"]["Get"]["DocumentChunk"]:
                documents.append({
                    "content": item["content"],
                    "filename": item["filename"],
                    "chunk_index": item["chunkIndex"],
                    "page_number": item["pageNumber"],
                    "section_title": item["sectionTitle"],
                    "document_id": item["documentId"],
                    "score": 1 - item["_additional"]["distance"],  # Convert distance to similarity
                    "metadata": eval(item["metadata"]) if item["metadata"] else {}
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error searching Weaviate: {e}")
            return []
    
    def delete_documents(self, document_ids: List[str]) -> bool:
        """Delete documents from Weaviate"""
        try:
            for doc_id in document_ids:
                self.client.data_object.delete(uuid=doc_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting documents from Weaviate: {e}")
            return False


class ChromaVectorStore(VectorStore):
    """ChromaDB vector database implementation"""
    
    def __init__(self):
        super().__init__()
        self.client = chromadb.PersistentClient(path=settings.chromadb_persist_directory)
        self.collection = self.client.get_or_create_collection(
            name="studymate_documents",
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_documents(self, documents: List[Dict[str, Any]], project_id: int) -> List[str]:
        """Add documents to ChromaDB"""
        try:
            ids = []
            texts = []
            metadatas = []
            embeddings = []
            
            for doc in documents:
                doc_id = str(uuid.uuid4())
                ids.append(doc_id)
                texts.append(doc['content'])
                
                metadata = {
                    "project_id": project_id,
                    "document_id": doc.get('document_id'),
                    "filename": doc.get('filename', ''),
                    "chunk_index": doc.get('chunk_index', 0),
                    "page_number": doc.get('page_number'),
                    "section_title": doc.get('section_title', ''),
                    **doc.get('metadata', {})
                }
                metadatas.append(metadata)
                
                # Generate embedding
                if isinstance(self.embeddings, OpenAIEmbeddings):
                    embedding = self.embeddings.embed_query(doc['content'])
                else:
                    embedding = self.embeddings.encode(doc['content']).tolist()
                embeddings.append(embedding)
            
            self.collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas,
                embeddings=embeddings
            )
            
            logger.info(f"Added {len(documents)} documents to ChromaDB")
            return ids
            
        except Exception as e:
            logger.error(f"Error adding documents to ChromaDB: {e}")
            raise
    
    def search(self, query: str, project_id: int, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents in ChromaDB"""
        try:
            # Generate query embedding
            if isinstance(self.embeddings, OpenAIEmbeddings):
                query_embedding = self.embeddings.embed_query(query)
            else:
                query_embedding = self.embeddings.encode(query).tolist()
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                where={"project_id": project_id},
                n_results=k
            )
            
            documents = []
            for i in range(len(results['ids'][0])):
                metadata = results['metadatas'][0][i]
                documents.append({
                    "content": results['documents'][0][i],
                    "filename": metadata.get('filename', ''),
                    "chunk_index": metadata.get('chunk_index', 0),
                    "page_number": metadata.get('page_number'),
                    "section_title": metadata.get('section_title', ''),
                    "document_id": metadata.get('document_id'),
                    "score": 1 - results['distances'][0][i],  # Convert distance to similarity
                    "metadata": metadata
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error searching ChromaDB: {e}")
            return []
    
    def delete_documents(self, document_ids: List[str]) -> bool:
        """Delete documents from ChromaDB"""
        try:
            self.collection.delete(ids=document_ids)
            return True
        except Exception as e:
            logger.error(f"Error deleting documents from ChromaDB: {e}")
            return False


def get_vector_store() -> VectorStore:
    """Factory function to get the configured vector store"""
    if settings.vector_db_type == "weaviate":
        return WeaviateVectorStore()
    else:
        return ChromaVectorStore()