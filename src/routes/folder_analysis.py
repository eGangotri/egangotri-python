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
import time
import json

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

def get_image_types_in_folder(folder_path: str) -> set:
    """Get all image types present in a folder."""
    image_types = set()
    for img_type in ImageType:
        if img_type != ImageType.ANY and has_image_files(folder_path, img_type):
            image_types.add(img_type)
    return image_types

def process_images_to_pdf(folder_path: str, output_path: str, img_type: ImageType, image_types: set = None) -> dict:
    """Convert images in a folder to PDF based on image type."""
    result = {
        'pdfs_created': [],
        'error': None,
        'image_types_found': list(image_types) if image_types else []
    }
    
    images = []
    extensions = get_extensions_for_type(img_type)
    
    print(f"\nProcessing folder: {folder_path}")
    print(f"Image type filter: {img_type.value}")
    
    for file in os.listdir(folder_path):
        file_lower = file.lower()
        if any(file_lower.endswith(ext) for ext in extensions):
            img_path = os.path.join(folder_path, file)
            try:
                print(f"  Loading image: {file}")
                if file_lower.endswith('.cr2'):
                    with rawpy.imread(img_path) as raw:
                        rgb = raw.postprocess()
                        pil_image = Image.fromarray(rgb)
                        images.append(pil_image)
                else:
                    img = Image.open(img_path)
                    if img.mode in ('RGBA', 'LA'):
                        background = Image.new('RGB', img.size, 'white')
                        background.paste(img, mask=img.split()[-1])
                        img = background
                    images.append(img)
            except Exception as e:
                error_msg = f"Error processing {img_path}: {str(e)}"
                print(f"  ❌ {error_msg}")
                result['error'] = error_msg
                # Clean up any loaded images before returning
                for img in images:
                    img.close()
                return result
    
    if not images:
        print("  ⚠️ No matching images found in folder")
        return result
    
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        suffix = f"-{img_type}s" if img_type != ImageType.JPG else ""
        pdf_path = f"{output_path}{suffix}.pdf"
        
        print(f"  Creating PDF: {os.path.basename(pdf_path)}")
        doc = fitz.open()
        for i, img in enumerate(images, 1):
            print(f"    Adding image {i}/{len(images)} to PDF...")
            img_bytes = img.tobytes("jpeg", "RGB")
            img_doc = fitz.open("jpg", img_bytes)
            pdfbytes = img_doc.convert_to_pdf()
            pdf_doc = fitz.open("pdf", pdfbytes)
            doc.insert_pdf(pdf_doc)
            # Close intermediate PDF documents
            img_doc.close()
            pdf_doc.close()
            # Close the PIL image
            img.close()
        
        doc.save(pdf_path)
        doc.close()
        result['pdfs_created'].append(pdf_path)
        print(f"  ✅ Successfully created PDF: {os.path.basename(pdf_path)}")
        
    except Exception as e:
        error_msg = f"Error creating PDF: {str(e)}"
        print(f"  ❌ {error_msg}")
        result['error'] = error_msg
        # Clean up any remaining images and documents
        for img in images:
            img.close()
        if 'doc' in locals():
            doc.close()
    
    return result

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
    start_time = time.time()
    
    print("\n🚀 Starting PDF conversion process...")
    print(f"Source folder: {request.src_folder}")
    print(f"Destination folder: {request.dest_folder}")
    print(f"Image type filter: {request.img_type.value}")
    
    if not os.path.exists(request.src_folder):
        raise HTTPException(status_code=404, detail="Source folder does not exist")
    
    if not os.path.isdir(request.src_folder):
        raise HTTPException(status_code=400, detail="Source path must be a directory")
    
    # Create base destination folder if it doesn't exist
    os.makedirs(request.dest_folder, exist_ok=True)
    
    report = {
        'src_folder': request.src_folder,
        'dest_folder': request.dest_folder,
        'img_type': request.img_type.value,
        'time_taken_seconds': 0,
        'total_folders': 0,
        'folders_with_images': 0,
        'pdfs_created': 0,
        'errors': [],
        'missed_folders': [],
        'multi_image_type_folders': [],
        'pdf_count_matches_folders': False,
        'processed_folders': []
    }
    
    try:
        print("\nScanning folders...")
        for root, dirs, files in os.walk(request.src_folder):
            if os.path.basename(root).startswith('.'):
                continue
            
            report['total_folders'] += 1
            
            # Calculate relative path to maintain directory structure
            rel_path = os.path.relpath(root, request.src_folder)
            dest_path = os.path.join(request.dest_folder, rel_path)
            
            # Get all image types in the folder
            image_types = get_image_types_in_folder(root)
            
            # Check if folder has relevant images
            has_target_images = has_image_files(root, request.img_type)
            
            if has_target_images:
                report['folders_with_images'] += 1
                folder_name = os.path.basename(root)
                pdf_base_path = os.path.join(dest_path, folder_name)
                
                # Handle multiple image types
                if len(image_types) > 1:
                    print(f"\n📁 Found multiple image types in {folder_name}:")
                    print(f"   Types: {', '.join(t.value for t in image_types)}")
                    report['multi_image_type_folders'].append({
                        'folder': root,
                        'image_types': [t.value for t in image_types]
                    })
                
                try:
                    result = process_images_to_pdf(root, pdf_base_path, request.img_type, image_types)
                    if result['error']:
                        report['errors'].append({
                            'folder': root,
                            'error': result['error']
                        })
                    else:
                        report['pdfs_created'] += len(result['pdfs_created'])
                        report['processed_folders'].append({
                            'folder': root,
                            'pdfs': result['pdfs_created'],
                            'image_types': [t.value for t in image_types]
                        })
                except Exception as e:
                    error_msg = f"Error processing folder {root}: {str(e)}"
                    print(f"❌ {error_msg}")
                    report['errors'].append({
                        'folder': root,
                        'error': error_msg
                    })
            elif image_types and request.img_type != ImageType.ANY:
                print(f"\n⚠️ Skipping folder {os.path.basename(root)}:")
                print(f"   Has types {[t.value for t in image_types]} but requested {request.img_type.value}")
                report['missed_folders'].append({
                    'folder': root,
                    'available_types': [t.value for t in image_types]
                })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Calculate final statistics
    report['time_taken_seconds'] = round(time.time() - start_time, 2)
    report['pdf_count_matches_folders'] = report['pdfs_created'] == report['folders_with_images']
    
    # Print final report
    print("\n📊 Conversion Process Summary:")
    print(f"Time taken: {report['time_taken_seconds']} seconds")
    print(f"Total folders scanned: {report['total_folders']}")
    print(f"Folders with matching images: {report['folders_with_images']}")
    print(f"PDFs created: {report['pdfs_created']}")
    print(f"Errors encountered: {len(report['errors'])}")
    print(f"Multi-image type folders: {len(report['multi_image_type_folders'])}")
    print(f"PDF count matches folder count: {'✅' if report['pdf_count_matches_folders'] else '❌'}")
    
    if report['errors']:
        print("\n❌ Errors encountered:")
        for error in report['errors']:
            print(f"  - {error['folder']}: {error['error']}")
    
    print("\n✨ Detailed JSON report:")
    print(json.dumps(report, indent=2))
    
    return report
