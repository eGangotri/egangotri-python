from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from pathlib import Path
from pypdf import PdfReader
from src.utils.image_constants import ImageType, get_extensions_for_type

router = APIRouter()

class FolderAnalysisRequest(BaseModel):
    folder_path: str
    img_type: ImageType = ImageType.ANY

def has_image_files(folder_path: str, img_type: ImageType) -> bool:
    extensions = get_extensions_for_type(img_type)
    for file in os.listdir(folder_path):
        if any(file.lower().endswith(ext) for ext in extensions):
            return True
    return False

def analyze_folder(base_path: str, img_type: ImageType):
    report = {
        'total_folder_count': 0,
        'folders_with_images': 0,
        'total_pdf_count': 0,
        'folders_missing_pdf': [],
        'erroneous_pdfs': [],
        'image_type_filter': img_type
    }
    
    for root, dirs, files in os.walk(base_path):
        if os.path.basename(root).startswith('.'):
            continue
            
        report['total_folder_count'] += 1
        folder_name = os.path.basename(root)
        
        # Check for images of specified type
        has_images = has_image_files(root, img_type)
        if has_images:
            report['folders_with_images'] += 1
            
            # Look for matching PDF
            pdf_found = False
            for file in files:
                if file.lower() == f"{folder_name.lower()}.pdf":
                    report['total_pdf_count'] += 1
                    pdf_found = True
                    
                    # Validate PDF
                    pdf_path = os.path.join(root, file)
                    try:
                        with open(pdf_path, 'rb') as pdf_file:
                            PdfReader(pdf_file)
                    except Exception as e:
                        report['erroneous_pdfs'].append({
                            'path': pdf_path,
                            'error': str(e)
                        })
                    break
            
            if not pdf_found:
                report['folders_missing_pdf'].append(root)
    
    report['matching_status'] = report['folders_with_images'] == report['total_pdf_count']
    
    return report

@router.post("/analyze-folder")
def analyze_folder_route(request: FolderAnalysisRequest):
    folder_path = request.folder_path
    
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="Folder path does not exist")
        
    if not os.path.isdir(folder_path):
        raise HTTPException(status_code=400, detail="Path must be a directory")
    
    try:
        report = analyze_folder(folder_path, request.img_type)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
