import os
import time
import json
import fitz
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator, model_validator
from typing import Dict, Any, Optional

router = APIRouter()

class PDFMergeRequest(BaseModel):
    first_pdf_path: str
    second_pdf_path: str
    third_pdf_path: Optional[str] = None
    
    @field_validator('first_pdf_path', 'second_pdf_path')
    @classmethod
    def validate_pdf_paths(cls, v):
        if not os.path.exists(v):
            raise ValueError(f"PDF path does not exist: {v}")
        if not v.lower().endswith('.pdf'):
            raise ValueError(f"File is not a PDF: {v}")
        if not os.path.isfile(v):
            raise ValueError(f"Path is not a file: {v}")
        return v
    
    @model_validator(mode='after')
    def validate_third_pdf_path(self) -> 'PDFMergeRequest':
        third_pdf_path = self.third_pdf_path
        if third_pdf_path:
            if not os.path.exists(third_pdf_path):
                raise ValueError(f"Third PDF path does not exist: {third_pdf_path}")
            if not third_pdf_path.lower().endswith('.pdf'):
                raise ValueError(f"Third file is not a PDF: {third_pdf_path}")
            if not os.path.isfile(third_pdf_path):
                raise ValueError(f"Third path is not a file: {third_pdf_path}")
        return self

@router.post("/mergePdfs", tags=["pdf-operations"])
async def merge_pdfs(request: PDFMergeRequest) -> Dict[str, Any]:
    """
    Merge two or three PDF files into one. The output will have the same name as the first PDF with "-merged.pdf" suffix.
    The third PDF is optional and will be included if provided.
    Optimized for handling large PDF files (4GB+).
    """
    start_time = time.time()
    
    try:
        # Create output filename based on the first PDF
        first_pdf_dir = os.path.dirname(request.first_pdf_path)
        first_pdf_name = os.path.basename(request.first_pdf_path)
        base_name, _ = os.path.splitext(first_pdf_name)
        output_path = os.path.join(first_pdf_dir, f"{base_name}-merged.pdf")
        
        print(f"[*] Starting PDF merge process")
        print(f"[*] First PDF: {request.first_pdf_path}")
        print(f"[*] Second PDF: {request.second_pdf_path}")
        if request.third_pdf_path:
            print(f"[*] Third PDF: {request.third_pdf_path}")
        print(f"[*] Output will be saved to: {output_path}")
        
        # Get file sizes for reporting
        first_pdf_size = os.path.getsize(request.first_pdf_path) / (1024 * 1024)  # Size in MB
        second_pdf_size = os.path.getsize(request.second_pdf_path) / (1024 * 1024)  # Size in MB
        third_pdf_size = None
        if request.third_pdf_path:
            third_pdf_size = os.path.getsize(request.third_pdf_path) / (1024 * 1024)  # Size in MB
            print(f"[*] Third PDF size: {third_pdf_size:.2f} MB")
        
        print(f"[*] First PDF size: {first_pdf_size:.2f} MB")
        print(f"[*] Second PDF size: {second_pdf_size:.2f} MB")
        
        # Open the PDFs
        print(f"[*] Opening first PDF document...")
        doc1 = fitz.open(request.first_pdf_path)
        
        print(f"[*] Opening second PDF document...")
        doc2 = fitz.open(request.second_pdf_path)
        
        doc3 = None
        if request.third_pdf_path:
            print(f"[*] Opening third PDF document...")
            doc3 = fitz.open(request.third_pdf_path)
        
        # Get page counts
        doc1_pages = len(doc1)
        doc2_pages = len(doc2)
        doc3_pages = 0
        if doc3:
            doc3_pages = len(doc3)
        
        total_pages = doc1_pages + doc2_pages + doc3_pages
        
        print(f"[*] First PDF page count: {doc1_pages}")
        print(f"[*] Second PDF page count: {doc2_pages}")
        if doc3:
            print(f"[*] Third PDF page count: {doc3_pages}")
        print(f"[*] Total pages in merged PDF: {total_pages}")
        
        # Create a new PDF with the content from the first PDF
        print(f"[*] Creating merged PDF...")
        result_pdf = fitz.open()
        
        # Calculate total number of PDFs to merge
        total_pdfs = 2 if not request.third_pdf_path else 3
        
        # Copy pages from first PDF with progress reporting
        print(f"[*] Copying pages from first PDF (1/{total_pdfs})...")
        for i in range(doc1_pages):
            if i % 10 == 0 or i == doc1_pages - 1:
                print(f"  - Copying page {i+1}/{doc1_pages} from first PDF...")
            result_pdf.insert_pdf(doc1, from_page=i, to_page=i)
        
        # Copy pages from second PDF with progress reporting
        print(f"[*] Copying pages from second PDF (2/{total_pdfs})...")
        for i in range(doc2_pages):
            if i % 10 == 0 or i == doc2_pages - 1:
                print(f"  - Copying page {i+1}/{doc2_pages} from second PDF...")
            result_pdf.insert_pdf(doc2, from_page=i, to_page=i)
        
        # Copy pages from third PDF if provided
        if doc3:
            print(f"[*] Copying pages from third PDF (3/{total_pdfs})...")
            for i in range(doc3_pages):
                if i % 10 == 0 or i == doc3_pages - 1:
                    print(f"  - Copying page {i+1}/{doc3_pages} from third PDF...")
                result_pdf.insert_pdf(doc3, from_page=i, to_page=i)
        
        # Save the merged PDF
        print(f"[*] Saving merged PDF to: {output_path}")
        result_pdf.save(output_path, garbage=4, deflate=True, clean=True)
        
        # Close all documents to free up resources
        doc1.close()
        doc2.close()
        if doc3:
            doc3.close()
        result_pdf.close()
        
        # Get file size of merged PDF
        merged_size = os.path.getsize(output_path) / (1024 * 1024)  # Size in MB
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"[*] Merge completed in {processing_time:.2f} seconds")
        print(f"[*] Merged PDF size: {merged_size:.2f} MB")
        
        # Prepare JSON response
        response = {
            "status": "success",
            "message": "PDF files merged successfully",
            "details": {
                "first_pdf": {
                    "path": request.first_pdf_path,
                    "size_mb": round(first_pdf_size, 2),
                    "pages": doc1_pages
                },
                "second_pdf": {
                    "path": request.second_pdf_path,
                    "size_mb": round(second_pdf_size, 2),
                    "pages": doc2_pages
                },
                "merged_pdf": {
                    "path": output_path,
                    "size_mb": round(merged_size, 2),
                    "pages": total_pages
                },
                "processing_time_seconds": round(processing_time, 2)
            }
        }
        
        # Add third PDF details to response if provided
        if request.third_pdf_path:
            response["details"]["third_pdf"] = {
                "path": request.third_pdf_path,
                "size_mb": round(third_pdf_size, 2),
                "pages": doc3_pages
            }
        
        print("\n[*] JSON Response:")
        print(json.dumps(response, indent=2))
        
        return response
        
    except Exception as e:
        print(f"[X] Error during PDF merge: {str(e)}")
        end_time = time.time()
        processing_time = end_time - start_time
        
        error_response = {
            "status": "error",
            "message": str(e),
            "details": {
                "first_pdf": request.first_pdf_path,
                "second_pdf": request.second_pdf_path,
                "processing_time_seconds": round(processing_time, 2)
            }
        }
        
        if request.third_pdf_path:
            error_response["details"]["third_pdf"] = request.third_pdf_path
        
        print("\n[*] JSON Error Response:")
        print(json.dumps(error_response, indent=2))
        
        raise HTTPException(status_code=500, detail=error_response)
