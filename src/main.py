import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.extractPdf.firstAndLastNPages import process_pdfs_in_folder
from src.copyFiles import copy_all_pdfs
from typing import Optional
from src.cr2ToPdf.cr2Img2Jpg import convert_cr2_folder_to_jpg
from src.routes.folder_analysis import router as folder_analysis_router

class ExtractFromPdfRequest(BaseModel):
    input_folder: str
    output_folder: str
    nFirstPages: int
    nLastPages: int


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


@app.post("/extractFromPdf")
def extract_from_pdf(request: ExtractFromPdfRequest):
    try:
        if not request.input_folder:
            raise HTTPException(
                status_code=400, detail="input_folder is required")
        if not request.output_folder:
            raise HTTPException(
                status_code=400, detail="output_folder is required")
        if request.nFirstPages is None:
            raise HTTPException(
                status_code=400, detail="nFirstPages is required")
        if request.nLastPages is None:
            raise HTTPException(
                status_code=400, detail="nLastPages is required")

        process_result = process_pdfs_in_folder(
            request.input_folder, request.output_folder, request.nFirstPages, request.nLastPages)
        return {
            "result": process_result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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