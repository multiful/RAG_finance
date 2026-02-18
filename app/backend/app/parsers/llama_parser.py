"""LlamaParse integration for advanced document parsing.

Handles: HWP, PDF with tables, images, and complex layouts.
Converts to structured markdown format.
"""
import os
import tempfile
from typing import List, Dict, Any, Optional
from pathlib import Path
import aiohttp
import aiofiles

from llama_parse import LlamaParse
from llama_index.core import Document as LlamaDocument

from app.core.config import settings


class LlamaDocumentParser:
    """Advanced document parser using LlamaParse."""
    
    def __init__(self):
        self.parser = None
        if settings.LLAMAPARSE_API_KEY:
            self.parser = LlamaParse(
                api_key=settings.LLAMAPARSE_API_KEY,
                result_type="markdown",
                verbose=True,
                language="ko"
            )
    
    async def parse_pdf(self, file_path: str) -> Dict[str, Any]:
        """Parse PDF file with table extraction.
        
        Returns:
            {
                "text": str,  # Full markdown text
                "pages": List[str],  # Per-page content
                "tables": List[Dict],  # Extracted tables
                "metadata": Dict  # Document metadata
            }
        """
        if not self.parser:
            return await self._fallback_pdf_parse(file_path)
        
        try:
            # Load and parse with LlamaParse
            documents = await self.parser.aload_data(file_path)
            
            if not documents:
                return await self._fallback_pdf_parse(file_path)
            
            # Combine all pages
            full_text = "\n\n".join([doc.text for doc in documents])
            
            # Extract tables using regex patterns
            tables = self._extract_tables_from_markdown(full_text)
            
            # Extract metadata
            metadata = {
                "total_pages": len(documents),
                "file_type": "pdf",
                "parser": "llamaparse"
            }
            
            return {
                "text": full_text,
                "pages": [doc.text for doc in documents],
                "tables": tables,
                "metadata": metadata
            }
            
        except Exception as e:
            print(f"LlamaParse error: {e}")
            return await self._fallback_pdf_parse(file_path)
    
    async def parse_hwp(self, file_path: str) -> Dict[str, Any]:
        """Parse HWP (Hancom) file.
        
        Note: HWP files are converted to PDF first if possible,
        otherwise uses fallback parser.
        """
        # Try to convert HWP to PDF using external tools
        pdf_path = await self._convert_hwp_to_pdf(file_path)
        
        if pdf_path:
            return await self.parse_pdf(pdf_path)
        
        # Fallback to basic text extraction
        return await self._fallback_hwp_parse(file_path)
    
    async def parse_file(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """Parse file based on type."""
        file_type = file_type.lower()
        
        if file_type == "pdf":
            return await self.parse_pdf(file_path)
        elif file_type in ["hwp", "hwpx"]:
            return await self.parse_hwp(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    def _extract_tables_from_markdown(self, markdown_text: str) -> List[Dict[str, Any]]:
        """Extract tables from markdown text."""
        import re
        
        tables = []
        
        # Find markdown tables
        table_pattern = r'\|([^\n]*)\|\n\|[-:\s|]+\|\n((?:\|[^\n]*\|\n?)*)'
        matches = re.findall(table_pattern, markdown_text)
        
        for i, (header_line, body_lines) in enumerate(matches):
            # Parse header
            headers = [h.strip() for h in header_line.split('|') if h.strip()]
            
            # Parse body rows
            rows = []
            for line in body_lines.strip().split('\n'):
                if line.strip():
                    cells = [c.strip() for c in line.split('|') if c.strip()]
                    if cells:
                        rows.append(cells)
            
            tables.append({
                "table_id": i,
                "headers": headers,
                "rows": rows,
                "row_count": len(rows),
                "column_count": len(headers)
            })
        
        return tables
    
    async def _fallback_pdf_parse(self, file_path: str) -> Dict[str, Any]:
        """Fallback PDF parser using pdfplumber."""
        import pdfplumber
        
        text_parts = []
        tables = []
        
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                # Extract text
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"## Page {i+1}\n\n{page_text}")
                
                # Extract tables
                page_tables = page.extract_tables()
                for table in page_tables:
                    if table and len(table) > 1:
                        tables.append({
                            "table_id": len(tables),
                            "headers": table[0] if table else [],
                            "rows": table[1:] if len(table) > 1 else [],
                            "row_count": len(table) - 1 if table else 0,
                            "column_count": len(table[0]) if table else 0,
                            "page": i + 1
                        })
        
        return {
            "text": "\n\n".join(text_parts),
            "pages": text_parts,
            "tables": tables,
            "metadata": {
                "total_pages": len(pdf.pages),
                "file_type": "pdf",
                "parser": "pdfplumber"
            }
        }
    
    async def _fallback_hwp_parse(self, file_path: str) -> Dict[str, Any]:
        """Fallback HWP parser using olefile."""
        try:
            import olefile
            
            if not olefile.isOleFile(file_path):
                return {
                    "text": "",
                    "pages": [],
                    "tables": [],
                    "metadata": {"error": "Not a valid HWP file"}
                }
            
            ole = olefile.OleFileIO(file_path)
            
            # Try to extract text from HWP streams
            text_parts = []
            
            # HWP files store text in "BodyText" stream
            if ole.exists('BodyText/Section0'):
                body_text = ole.openstream('BodyText/Section0').read()
                # HWP uses UTF-16LE encoding
                try:
                    decoded = body_text.decode('utf-16le', errors='ignore')
                    # Remove control characters
                    import re
                    cleaned = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', decoded)
                    text_parts.append(cleaned)
                except:
                    pass
            
            ole.close()
            
            full_text = "\n\n".join(text_parts)
            
            return {
                "text": full_text,
                "pages": text_parts,
                "tables": [],  # HWP table extraction is complex
                "metadata": {
                    "file_type": "hwp",
                    "parser": "olefile"
                }
            }
            
        except ImportError:
            return {
                "text": "",
                "pages": [],
                "tables": [],
                "metadata": {"error": "olefile not installed"}
            }
    
    async def _convert_hwp_to_pdf(self, file_path: str) -> Optional[str]:
        """Convert HWP to PDF using external tools."""
        # This would require external tools like:
        # - hwp5pdf (Python library)
        # - LibreOffice command line
        # - Hancom Office automation
        
        # For now, return None to use fallback
        return None


# ============ Chunking with Table Preservation ============

class TableAwareChunker:
    """Chunk documents while preserving table structure."""
    
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_document(self, parsed_doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create chunks from parsed document.
        
        Preserves table boundaries and section headers.
        """
        chunks = []
        text = parsed_doc.get("text", "")
        tables = parsed_doc.get("tables", [])
        
        # Split by sections (## Page X or ## Section X)
        import re
        sections = re.split(r'\n##?\s+', text)
        
        chunk_index = 0
        current_chunk_text = ""
        current_chunk_tables = []
        
        for section in sections:
            if not section.strip():
                continue
            
            # Check if adding this section would exceed chunk size
            if len(current_chunk_text) + len(section) > self.chunk_size and current_chunk_text:
                # Save current chunk
                chunks.append({
                    "chunk_index": chunk_index,
                    "chunk_text": current_chunk_text.strip(),
                    "tables": current_chunk_tables,
                    "token_count": len(current_chunk_text.split())
                })
                chunk_index += 1
                
                # Start new chunk with overlap
                words = current_chunk_text.split()
                overlap_text = " ".join(words[-self.chunk_overlap:]) if len(words) > self.chunk_overlap else current_chunk_text
                current_chunk_text = overlap_text + "\n\n" + section
                current_chunk_tables = []
            else:
                current_chunk_text += "\n\n" + section
            
            # Check if any tables belong to this section
            for table in tables:
                table_text = self._table_to_text(table)
                if table_text in section or any(h in section for h in table.get("headers", [])):
                    current_chunk_tables.append(table)
        
        # Save final chunk
        if current_chunk_text.strip():
            chunks.append({
                "chunk_index": chunk_index,
                "chunk_text": current_chunk_text.strip(),
                "tables": current_chunk_tables,
                "token_count": len(current_chunk_text.split())
            })
        
        return chunks
    
    def _table_to_text(self, table: Dict[str, Any]) -> str:
        """Convert table to text representation."""
        lines = []
        headers = table.get("headers", [])
        rows = table.get("rows", [])
        
        if headers:
            lines.append(" | ".join(headers))
        
        for row in rows:
            lines.append(" | ".join(str(cell) for cell in row))
        
        return "\n".join(lines)


# ============ Public API ============

_llama_parser: Optional[LlamaDocumentParser] = None
_chunker: Optional[TableAwareChunker] = None

def get_parser() -> LlamaDocumentParser:
    """Get singleton parser instance."""
    global _llama_parser
    if _llama_parser is None:
        _llama_parser = LlamaDocumentParser()
    return _llama_parser

def get_chunker() -> TableAwareChunker:
    """Get singleton chunker instance."""
    global _chunker
    if _chunker is None:
        _chunker = TableAwareChunker()
    return _chunker

async def parse_and_chunk_document(file_path: str, file_type: str) -> List[Dict[str, Any]]:
    """Parse document and create chunks.
    
    Args:
        file_path: Path to document file
        file_type: File type (pdf, hwp, etc.)
        
    Returns:
        List of chunks with metadata
    """
    parser = get_parser()
    chunker = get_chunker()
    
    # Parse document
    parsed = await parser.parse_file(file_path, file_type)
    
    # Create chunks
    chunks = chunker.chunk_document(parsed)
    
    # Add document-level metadata
    for chunk in chunks:
        chunk["metadata"] = {
            "file_type": file_type,
            "parser": parsed.get("metadata", {}).get("parser", "unknown"),
            "total_pages": parsed.get("metadata", {}).get("total_pages", 0)
        }
    
    return chunks
