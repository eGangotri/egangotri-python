from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from pathlib import Path
from pypdf import PdfReader
import fitz
from PIL import Image
import rawpy
from src.utils.image_constants import ImageType, get_extensions_for_type
import shutil

router = APIRouter()

class FolderAnalysisRequest(BaseModel):
    folder_path: str
    img_type: ImageType = ImageType.ANY

class ImageConversionRequest(BaseModel):
    src_folder: str
    dest_folder: str
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

def process_images_to_pdf(folder_path: str, output_path: str, img_type: ImageType) -> list:
    """Convert images in a folder to PDF based on image type."""
    images = []
    extensions = get_extensions_for_type(img_type)
    
    for file in os.listdir(folder_path):
        file_lower = file.lower()
        if any(file_lower.endswith(ext) for ext in extensions):
            img_path = os.path.join(folder_path, file)
            if file_lower.endswith('.cr2'):
                with rawpy.imread(img_path) as raw:
                    rgb = raw.postprocess()
                    pil_image = Image.fromarray(rgb)
                    images.append(pil_image)
            else:
                try:
                    img = Image.open(img_path)
                    if img.mode in ('RGBA', 'LA'):
                        background = Image.new('RGB', img.size, 'white')
                        background.paste(img, mask=img.split()[-1])
                        img = background
                    images.append(img)
                except Exception as e:
                    print(f"Error processing {img_path}: {str(e)}")
    
    if not images:
        return []
    
    # Create the output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save images as PDF
    if images:
        suffix = f"-{img_type}s" if img_type != ImageType.JPG else ""
        pdf_path = f"{output_path}{suffix}.pdf"
        
        doc = fitz.open()
        for img in images:
            img_bytes = img.tobytes("jpeg", "RGB")
            img_doc = fitz.open("jpg", img_bytes)
            pdfbytes = img_doc.convert_to_pdf()
            pdf_doc = fitz.open("pdf", pdfbytes)
            doc.insert_pdf(pdf_doc)
        
        doc.save(pdf_path)
        doc.close()
        return [pdf_path]
    
    return []

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

@router.post("/convert-folder-to-pdf")
async def convert_folder_to_pdf(request: ImageConversionRequest):
    if not os.path.exists(request.src_folder):
        raise HTTPException(status_code=404, detail="Source folder does not exist")
    
    if not os.path.isdir(request.src_folder):
        raise HTTPException(status_code=400, detail="Source path must be a directory")
    
    # Create base destination folder if it doesn't exist
    os.makedirs(request.dest_folder, exist_ok=True)
    
    conversion_report = {
        'processed_folders': 0,
        'generated_pdfs': [],
        'errors': []
    }
    
    try:
        for root, dirs, files in os.walk(request.src_folder):
            if os.path.basename(root).startswith('.'):
                continue
                
            # Calculate relative path to maintain directory structure
            rel_path = os.path.relpath(root, request.src_folder)
            dest_path = os.path.join(request.dest_folder, rel_path)
            
            # Check if folder has relevant images
            if has_image_files(root, request.img_type):
                folder_name = os.path.basename(root)
                pdf_base_path = os.path.join(dest_path, folder_name)
                
                try:
                    pdfs = process_images_to_pdf(root, pdf_base_path, request.img_type)
                    if pdfs:
                        conversion_report['processed_folders'] += 1
                        conversion_report['generated_pdfs'].extend(pdfs)
                except Exception as e:
                    conversion_report['errors'].append({
                        'folder': root,
                        'error': str(e)
                    })
        
        return conversion_report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
