import os
import re
from typing import List, Dict, Any, Optional
from io import BytesIO

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from PIL import Image
    import pytesseract
except ImportError:
    pytesseract = None


class RAGPDFParser:
    """
    RAG (Retrieval-Augmented Generation) 파이프라인을 위해 최적화된 PDF 파서 클래스.
    텍스트 추출뿐만 아니라, 헤더/푸터 필터링, 레이아웃(글꼴 크기) 기반 구조화, 
    테이블 추출, 스캔된 PDF를 위한 OCR 폴백(fallback) 기능을 제공합니다.
    """

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

    def extract_text_with_structure(self) -> List[Dict[str, Any]]:
        """
        PyMuPDF(fitz)를 사용하여 PDF의 구조적 정보(글꼴 크기, 위치 등)를 함께 추출합니다.
        글꼴 크기를 통해 제목(Header)과 본문(Body)을 구분할 수 있어 세맨틱 청킹(Semantic Chunking)에 유리합니다.
        """
        if fitz is None:
            raise ImportError(
                "PyMuPDF가 설치되어 있지 않습니다. 'pip install pymupdf'를 실행해 주세요."
            )

        doc = fitz.open(self.pdf_path)
        documents = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            # 'dict' 형태로 페이지를 로드하면 블록, 라인, 스팬 단위의 상세 메타데이터를 얻을 수 있습니다.
            page_dict = page.get_text("dict")
            blocks = page_dict.get("blocks", [])

            for block_idx, block in enumerate(blocks):
                # 0: 텍스트 블록, 1: 이미지 블록
                if block.get("type") != 0:
                    continue

                block_text = ""
                max_font_size = 0.0
                is_bold = False

                for line in block.get("lines", []):
                    line_text = ""
                    for span in line.get("spans", []):
                        span_text = span.get("text", "").strip()
                        if not span_text:
                            continue
                        
                        line_text += " " + span_text
                        
                        # 가장 큰 폰트 크기를 해당 블록의 대표 폰트 크기로 설정
                        font_size = span.get("size", 0.0)
                        if font_size > max_font_size:
                            max_font_size = font_size
                        
                        # 볼드체 여부 확인
                        font_name = span.get("font", "").lower()
                        if "bold" in font_name or "black" in font_name:
                            is_bold = True
                    
                    line_text = line_text.strip()
                    if line_text:
                        block_text += line_text + "\n"

                block_text = block_text.strip()
                if not block_text:
                    continue

                # 헤더/푸터 및 단순 페이지 번호 필터링 예시 (패턴 매칭)
                if self._is_header_footer(block_text, page_num + 1):
                    continue

                # 메타데이터 구조화
                documents.append({
                    "text": block_text,
                    "metadata": {
                        "source": os.path.basename(self.pdf_path),
                        "page": page_num + 1,
                        "block_index": block_idx,
                        "font_size": round(max_font_size, 2),
                        "is_bold": is_bold,
                        # 폰트 크기 기반으로 임시 레벨 분류 (일반 본문은 보통 9~11pt)
                        "element_type": "heading" if max_font_size > 12.0 else "paragraph"
                    }
                })

        doc.close()
        return documents

    def extract_tables_as_markdown(self) -> List[Dict[str, Any]]:
        """
        pdfplumber를 사용하여 페이지 내의 표(Table) 데이터를 마크다운 포맷으로 추출합니다.
        LLM은 텍스트 줄글보다 표 형식(특히 마크다운)의 구조화된 데이터를 훨씬 더 잘 이해합니다.
        """
        if pdfplumber is None:
            raise ImportError(
                "pdfplumber가 설치되어 있지 않습니다. 'pip install pdfplumber'를 실행해 주세요."
            )

        tables_data = []
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                tables = page.find_tables()
                for table_idx, table in enumerate(tables):
                    table_content = table.extract()
                    if not table_content or len(table_content) < 2:
                        continue

                    # 마크다운 변환
                    markdown_table = self._convert_to_markdown_table(table_content)
                    
                    tables_data.append({
                        "text": markdown_table,
                        "metadata": {
                            "source": os.path.basename(self.pdf_path),
                            "page": page_idx + 1,
                            "table_index": table_idx,
                            "element_type": "table"
                        }
                    })
        return tables_data

    def extract_scanned_pdf_with_ocr(self, lang: str = "kor+eng") -> List[Dict[str, Any]]:
        """
        텍스트 레이어가 없는 스캔본 PDF의 경우, pytesseract OCR을 사용해 텍스트를 추출합니다.
        (사전에 시스템에 tesseract-ocr 엔진이 설치되어 있어야 합니다.)
        """
        if fitz is None or pytesseract is None:
            raise ImportError(
                "fitz(PyMuPDF) 또는 pytesseract가 설치되어 있지 않습니다. 필요 패키지를 확인하세요."
            )

        doc = fitz.open(self.pdf_path)
        documents = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            # 페이지를 고해상도 이미지(pixmap)로 렌더링
            pix = page.get_pixmap(dpi=150)
            img_data = pix.tobytes("png")
            
            # PIL Image로 변환
            img = Image.open(BytesIO(img_data))
            
            # OCR 수행
            text = pytesseract.image_to_string(img, lang=lang)
            text = text.strip()

            if text:
                documents.append({
                    "text": text,
                    "metadata": {
                        "source": os.path.basename(self.pdf_path),
                        "page": page_num + 1,
                        "element_type": "ocr_text"
                    }
                })
        
        doc.close()
        return documents

    def _is_header_footer(self, text: str, page_num: int) -> bool:
        """단순 페이지 번호나 정형화된 헤더/푸터를 필터링하는 헬퍼 메서드"""
        text_clean = text.strip()
        # 1. 단일 숫자 (페이지 번호)
        if re.match(r"^\d+$", text_clean):
            return True
        # 2. - 1 - 형태의 페이지 번호
        if re.match(r"^-\s*\d+\s*-$", text_clean):
            return True
        # 3. "Page X of Y" 형태
        if re.search(r"(?i)page\s*\d+\s*(of|/)\s*\d+", text_clean):
            return True
        return False

    def _convert_to_markdown_table(self, table_content: List[List[Optional[str]]]) -> str:
        """추출된 2차원 리스트 형태의 표를 마크다운 텍스트로 변환"""
        # None 값을 빈 문자열로 처리하고 엔터 제거
        cleaned_table = []
        for row in table_content:
            cleaned_row = []
            for cell in row:
                if cell is None:
                    cleaned_row.append("")
                else:
                    # 마크다운 표 깨짐 방지를 위해 파이프(|) 문자 제거 및 공백 정리
                    cell_text = str(cell).replace("|", "\\|").replace("\n", " ").strip()
                    cleaned_row.append(cell_text)
            cleaned_table.append(cleaned_row)

        headers = cleaned_table[0]
        rows = cleaned_table[1:]

        # 헤더 생성
        markdown = "| " + " | ".join(headers) + " |\n"
        # 구분선 생성
        markdown += "| " + " | ".join(["---"] * len(headers)) + " |\n"
        # 데이터 행 추가
        for row in rows:
            # 행의 셀 개수가 헤더 개수와 다른 경우 맞춤
            if len(row) < len(headers):
                row += [""] * (len(headers) - len(row))
            elif len(row) > len(headers):
                row = row[:len(headers)]
            markdown += "| " + " | ".join(row) + " |\n"

        return markdown


if __name__ == "__main__":
    print("PDF 파서가 성공적으로 로드되었습니다.")
