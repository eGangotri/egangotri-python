from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.extractPdf.firstAndLastNPages import process_pdfs_in_folder
class ExtractFromPdfRequest(BaseModel):
    input_folder: str
    output_folder: str
    nFirstPages: int
    nLastPages: int
app = FastAPI()


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
            raise HTTPException(status_code=400, detail="input_folder is required")
        if not request.output_folder:
            raise HTTPException(status_code=400, detail="output_folder is required")
        if request.nFirstPages is None:
            raise HTTPException(status_code=400, detail="nFirstPages is required")
        if request.nLastPages is None:
            raise HTTPException(status_code=400, detail="nLastPages is required")

        process_result = process_pdfs_in_folder(request.input_folder, request.output_folder, request.nFirstPages, request.nLastPages)
        return {
            "result":process_result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
