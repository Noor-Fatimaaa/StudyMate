import fitz  # PyMuPDF
import docx
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional, Tuple
import re
from pathlib import Path
import logging
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.config import settings

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Handles parsing and chunking of various document types"""
    
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def process_document(self, file_path: str, filename: str) -> Dict[str, Any]:
        """
        Process a document and extract text with metadata
        
        Args:
            file_path: Path to the uploaded file
            filename: Original filename
            
        Returns:
            Dict containing extracted text, metadata, and chunks
        """
        file_extension = Path(filename).suffix.lower()
        
        try:
            if file_extension == '.pdf':
                return self._process_pdf(file_path)
            elif file_extension == '.docx':
                return self._process_docx(file_path)
            elif file_extension == '.txt':
                return self._process_txt(file_path)
            elif file_extension == '.html':
                return self._process_html(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
                
        except Exception as e:
            logger.error(f"Error processing document {filename}: {str(e)}")
            raise
    
    def _process_pdf(self, file_path: str) -> Dict[str, Any]:
        """Process PDF file using PyMuPDF"""
        doc = fitz.open(file_path)
        
        pages = []
        full_text = ""
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            # Clean up text
            text = self._clean_text(text)
            
            if text.strip():
                pages.append({
                    'page_number': page_num + 1,
                    'content': text,
                    'metadata': {
                        'page_width': page.rect.width,
                        'page_height': page.rect.height
                    }
                })
                full_text += f"\n\nPage {page_num + 1}:\n{text}"
        
        doc.close()
        
        # Create chunks
        chunks = self._create_chunks(full_text, pages)
        
        return {
            'full_text': full_text,
            'pages': pages,
            'chunks': chunks,
            'page_count': len(pages),
            'metadata': {
                'total_pages': len(doc),
                'file_type': 'pdf'
            }
        }
    
    def _process_docx(self, file_path: str) -> Dict[str, Any]:
        """Process DOCX file using python-docx"""
        doc = docx.Document(file_path)
        
        full_text = ""
        sections = []
        current_section = {"title": None, "content": ""}
        
        for paragraph in doc.paragraphs:
            text = paragraph.text.strip()
            if not text:
                continue
            
            # Check if this looks like a heading
            if paragraph.style.name.startswith('Heading') or len(text) < 100 and text.isupper():
                if current_section["content"]:
                    sections.append(current_section)
                current_section = {"title": text, "content": ""}
            else:
                current_section["content"] += f"{text}\n"
            
            full_text += f"{text}\n"
        
        # Add the last section
        if current_section["content"]:
            sections.append(current_section)
        
        # Create chunks
        chunks = self._create_chunks(full_text, sections)
        
        return {
            'full_text': full_text,
            'sections': sections,
            'chunks': chunks,
            'page_count': 1,  # DOCX doesn't have clear page breaks
            'metadata': {
                'total_sections': len(sections),
                'file_type': 'docx'
            }
        }
    
    def _process_txt(self, file_path: str) -> Dict[str, Any]:
        """Process TXT file"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            full_text = f.read()
        
        # Clean text
        full_text = self._clean_text(full_text)
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in full_text.split('\n\n') if p.strip()]
        
        # Create chunks
        chunks = self._create_chunks(full_text)
        
        return {
            'full_text': full_text,
            'paragraphs': paragraphs,
            'chunks': chunks,
            'page_count': 1,
            'metadata': {
                'total_paragraphs': len(paragraphs),
                'file_type': 'txt'
            }
        }
    
    def _process_html(self, file_path: str) -> Dict[str, Any]:
        """Process HTML file using BeautifulSoup"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Extract text
        full_text = soup.get_text()
        full_text = self._clean_text(full_text)
        
        # Extract sections based on headings
        sections = []
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        for heading in headings:
            section_text = ""
            current = heading.next_sibling
            
            while current and current.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                if hasattr(current, 'get_text'):
                    section_text += current.get_text() + "\n"
                current = current.next_sibling
            
            if section_text.strip():
                sections.append({
                    'title': heading.get_text().strip(),
                    'content': section_text.strip()
                })
        
        # Create chunks
        chunks = self._create_chunks(full_text, sections)
        
        return {
            'full_text': full_text,
            'sections': sections,
            'chunks': chunks,
            'page_count': 1,
            'metadata': {
                'total_sections': len(sections),
                'file_type': 'html'
            }
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        # Remove special characters that might cause issues
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', text)
        
        return text.strip()
    
    def _create_chunks(self, full_text: str, sections: Optional[List[Dict]] = None) -> List[Dict[str, Any]]:
        """Create text chunks for vector storage"""
        chunks = []
        
        # Split text into chunks
        text_chunks = self.text_splitter.split_text(full_text)
        
        for i, chunk_text in enumerate(text_chunks):
            chunk = {
                'content': chunk_text,
                'chunk_index': i,
                'metadata': {
                    'chunk_size': len(chunk_text),
                    'chunk_number': i + 1,
                    'total_chunks': len(text_chunks)
                }
            }
            
            # Try to identify which section/page this chunk belongs to
            if sections:
                for section in sections:
                    section_content = section.get('content', '')
                    if section_content and chunk_text in section_content:
                        chunk['section_title'] = section.get('title')
                        chunk['page_number'] = section.get('page_number')
                        break
            
            chunks.append(chunk)
        
        return chunks