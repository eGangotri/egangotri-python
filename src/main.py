import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator
from src.extractPdf.first_and_last_n_pages import process_pdfs_in_folder
from src.copyFiles import copy_all_pdfs
from typing import Optional, List, Dict
from src.cr2ToPdf.cr2Img2Jpg import convert_cr2_folder_to_jpg
from src.utils.print_logger import PrintLogger
from src.routes.img_to_pdf import img_folder_router, verify_router, pdf_merge_router
import os

# Initialize print logging
PrintLogger()

class ExtractFromPdfRequest(BaseModel):
    input_folder: str = Field(..., description="Path to input folder containing PDFs")
    output_folder: str = Field(..., description="Path where extracted PDFs will be saved")
    nFirstPages: int = Field(..., description="Number of pages to extract from start", ge=0)
    nLastPages: int = Field(..., description="Number of pages to extract from end", ge=0)
    reducePdfSizeAlso: bool = Field(default=True, description="Whether to reduce the output PDF size to 70% of original")
    commonRunId: Optional[str] = Field(default=None, description="Common run ID for tracking")
    runId: Optional[str] = Field(default=None, description="Run ID for tracking")
    
    @model_validator(mode='after')
    def validate_paths(self) -> 'ExtractFromPdfRequest':
        if not self.input_folder:
            raise ValueError("Input folder path cannot be empty")
        if not os.path.exists(self.input_folder):
            raise ValueError(f"Input folder '{self.input_folder}' does not exist")
        if not os.path.isdir(self.input_folder):
            raise ValueError(f"'{self.input_folder}' is not a directory")

        if not self.output_folder:
            raise ValueError("Output folder path cannot be empty")
        os.makedirs(self.output_folder, exist_ok=True)

        return self

class ProcessingDetail(BaseModel):
    file: str
    status: str
    original_pages: Optional[int] = None
    pages_extracted: Optional[int] = None
    error: Optional[str] = None

class ExtractFromPdfResponse(BaseModel):
    totalFiles: int = Field(..., description="Total number of PDF files found")
    processedFiles: int = Field(..., description="Number of files successfully processed")
    errors: int = Field(..., description="Number of files that failed to process")
    input_folder: str = Field(..., description="Input folder path")
    output_folder: str = Field(..., description="Output folder path where PDFs are saved")
    log_messages: List[str] = Field(default_factory=list, description="Detailed progress and error messages")
    start_time: str = Field(..., description="Processing start time")
    duration_seconds: float = Field(..., description="Total processing time in seconds")
    processing_details: List[ProcessingDetail] = Field(default_factory=list, description="Detailed processing information for each file")

class CopyPdfRequest(BaseModel):
    input_folder: str
    output_folder: Optional[str] = None

class CR2ToPdfRequest(BaseModel):
    cr2_folder: str
    output_jpg_path: str

class BulkUploadPdfRequest(BaseModel):
    directory_path: str = Field(..., description="Path to directory containing PDFs")
    metadata: Dict = Field(..., description="Metadata for the upload")
    accepted_extensions: List[str] = Field(default=[".pdf"], description="List of accepted file extensions")

    @model_validator(mode='after')
    def validate_paths(self) -> 'BulkUploadPdfRequest':
        if not self.directory_path:
            raise ValueError("Directory path cannot be empty")
        if not os.path.exists(self.directory_path):
            raise ValueError(f"Directory '{self.directory_path}' does not exist")
        if not os.path.isdir(self.directory_path):
            raise ValueError(f"'{self.directory_path}' is not a directory")
        return self

app = FastAPI()
app.include_router(img_folder_router, tags=["img-folder-to-pdf"])
app.include_router(pdf_merge_router, tags=["pdf-operations"])
app.include_router(verify_router, tags=["verify-img-to-pdf"])


@app.get("/")
def read_root():
    return {"egangtri-python": "server is running"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}


@app.post("/extractFromPdf", response_model=ExtractFromPdfResponse)
def extract_from_pdf(request: ExtractFromPdfRequest):
    print(f"Extracting first {request.nFirstPages} and last {request.nLastPages} pages from PDFs in {request.input_folder}")
    try:
        result = process_pdfs_in_folder(
            request.input_folder, 
            request.output_folder, 
            request.nFirstPages, 
            request.nLastPages,
            reduce_size=request.reducePdfSizeAlso,
            commonRunId=request.commonRunId,
            runId=request.runId
        )
        return ExtractFromPdfResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/copyOnlyPdfs")
def copyOnlyPdfs(request: CopyPdfRequest):
    try:
        if not request.input_folder:
            raise HTTPException(
                status_code=400, detail="input_folder is required")
        copy_res = copy_all_pdfs(request.input_folder, request.output_folder)
        print(f"Copied: {json.dumps(copy_res, indent=4)}")
        
        return {
            "result": copy_res
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/cr2ToJpg")
def convertCr2ToJpgs(request: CR2ToPdfRequest):
    try:
        if not request.cr2_folder:
            raise HTTPException(
                status_code=400, detail="cr2_folder is required")
        cr2ToPdfRes = convert_cr2_folder_to_jpg(request.cr2_folder, request.output_jpg_path)
        print(f"Cr2 Converted: {json.dumps(cr2ToPdfRes, indent=4)}")
        
        return {
            "result": cr2ToPdfRes
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
