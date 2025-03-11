import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator
from src.extractPdf.firstAndLastNPages import process_pdfs_in_folder
from src.copyFiles import copy_all_pdfs
from typing import Optional, List, Dict
from src.cr2ToPdf.cr2Img2Jpg import convert_cr2_folder_to_jpg
from src.routes.img_folder_to_pdf import router as folder_analysis_router
from src.utils.print_logger import PrintLogger
import os

# Initialize print logging
PrintLogger()

class ExtractFromPdfRequest(BaseModel):
    input_folder: str = Field(..., description="Path to input folder containing PDFs")
    output_folder: str = Field(..., description="Path where extracted PDFs will be saved")
    nFirstPages: int = Field(..., description="Number of pages to extract from start", ge=0)
    nLastPages: int = Field(..., description="Number of pages to extract from end", ge=0)

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

class ExtractFromPdfResponse(BaseModel):
    totalFiles: int
    processedFiles: int
    errors: int
    input_folder: str
    output_folder: str
    log_messages: List[str]

class CopyPdfRequest(BaseModel):
    input_folder: str
    output_folder: Optional[str] = None

class CR2ToPdfRequest(BaseModel):
    cr2_folder: str
    output_jpg_path: str

app = FastAPI()
app.include_router(folder_analysis_router, tags=["folder-analysis"])


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}


@app.post("/extractFromPdf", response_model=ExtractFromPdfResponse)
def extract_from_pdf(request: ExtractFromPdfRequest):
    try:
        result = process_pdfs_in_folder(
            request.input_folder, 
            request.output_folder, 
            request.nFirstPages, 
            request.nLastPages
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