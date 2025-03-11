from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from pathlib import Path
from pypdf import PdfReader
import fitz
from PIL import Image
import rawpy
import json
import time
from typing import List, Dict, Set
from enum import Enum
from src.utils.image_constants import ImageType, get_extensions_for_type
import shutil

router = APIRouter()

class FolderAnalysisRequest(BaseModel):
    folder_path: str
    dest_folder: str
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

def count_images_in_folder(folder_path: str, img_type: ImageType) -> int:
    """Count the number of images of specified type in a folder."""
    count = 0
    extensions = get_extensions_for_type(img_type)
    for file in os.listdir(folder_path):
        if any(file.lower().endswith(ext) for ext in extensions):
            count += 1
    return count

def print_json_report(report: dict):
    """Print the report in JSON format for machine consumption."""
    json_output = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'execution_stats': {
            'processing_time_seconds': report['processing_time_seconds'],
            'total_folders': report['total_folder_count'],
            'folders_with_images': report['folders_with_images'],
            'total_images': report['total_image_count'],
            'total_pdfs': report['total_pdf_count'],
            'missing_pdfs': report['folders_missing_pdf_count'],
            'mismatched_pages': len(report['mismatched_page_counts']),
            'pdf_errors': len(report['erroneous_pdfs']),
            'multi_type_folders': len(report['multi_type_folders'])
        },
        'image_type_stats': report['image_type_stats'],
        'issues': {
            'missing_pdfs': [
                {
                    'source_folder': item['source'],
                    'expected_pdf': item['expected_pdf'],
                    'image_count': item['image_count'],
                    'image_types': item['image_types']
                } for item in report['folders_missing_pdf']
            ],
            'mismatched_pages': [
                {
                    'folder': item['folder_path'],
                    'pdf': item['pdf_path'],
                    'image_count': item['image_count'],
                    'pdf_pages': item['pdf_pages'],
                    'image_types': item['image_types']
                } for item in report['mismatched_page_counts']
            ],
            'pdf_errors': [
                {
                    'pdf': item['path'],
                    'error': item['error']
                } for item in report['erroneous_pdfs']
            ]
        },
        'multi_type_folders': [
            {
                'folder': item['path'],
                'image_types': item['types']
            } for item in report['multi_type_folders']
        ],
        'status': {
            'success': report['matching_status'],
            'image_type_filter': report['image_type_filter'].value
        }
    }
    print("\n📋 JSON Report:")
    print(json.dumps(json_output, indent=2))

def verfiyImgtoPdf(src_path: str, dest_path: str, img_type: ImageType):
    start_time = time.time()
    
    report = {
        'total_folder_count': 0,
        'folders_with_images': 0,
        'total_pdf_count': 0,
        'total_image_count': 0,
        'folders_missing_pdf_count': 0,
        'erroneous_pdfs': [],
        'mismatched_page_counts': [],
        'image_type_filter': img_type,
        'folders_missing_pdf': [],
        'multi_type_folders': [],
        'processing_time_seconds': 0,
        'image_type_stats': {}
    }
    
    print(f"\n🔍 Starting verification...")
    print(f"Source path: {src_path}")
    print(f"Destination path: {dest_path}")
    print(f"Image type filter: {img_type.value}\n")
    
    for root, dirs, files in os.walk(src_path):
        if os.path.basename(root).startswith('.'):
            continue
            
        report['total_folder_count'] += 1
        
        # Get relative path from src_path to create corresponding dest path
        rel_path = os.path.relpath(root, src_path)
        folder_name = os.path.basename(root)
        dest_dir = os.path.join(dest_path, rel_path)
        
        # Check for multiple image types
        image_types_present = get_image_types_in_folder(root)
        has_multiple_types = len(image_types_present) > 1
        
        # Update image type statistics
        for img_t in image_types_present:
            if img_t != ImageType.ANY:
                type_count = count_images_in_folder(root, img_t)
                if img_t.value not in report['image_type_stats']:
                    report['image_type_stats'][img_t.value] = {
                        'count': 0,
                        'folders': 0
                    }
                report['image_type_stats'][img_t.value]['count'] += type_count
                report['image_type_stats'][img_t.value]['folders'] += 1
        
        if has_multiple_types:
            report['multi_type_folders'].append({
                'path': root,
                'types': [t.value for t in image_types_present]
            })
            print(f"Checking folder: {rel_path} (Multiple image types: {', '.join(t.value for t in image_types_present)})")
        else:
            print(f"Checking folder: {rel_path}")
        
        # Check for images of specified type in source directory
        has_images = has_image_files(root, img_type)
        if has_images:
            report['folders_with_images'] += 1
            image_count = count_images_in_folder(root, img_type)
            report['total_image_count'] += image_count
            print(f"  ├─ Found {image_count} images{' (filtered by type)' if has_multiple_types else ''}")
            
            # Look for matching PDF in destination directory
            pdf_found = False
            expected_pdf = os.path.join(dest_dir, f"{folder_name}.pdf")
            
            if os.path.exists(expected_pdf):
                report['total_pdf_count'] += 1
                pdf_found = True
                
                # Validate PDF and check page count
                try:
                    # First validate with PdfReader
                    with open(expected_pdf, 'rb') as pdf_file:
                        PdfReader(pdf_file)
                    
                    # Then check page count with fitz
                    with fitz.open(expected_pdf) as pdf_doc:
                        pdf_page_count = len(pdf_doc)
                        print(f"  ├─ Found PDF with {pdf_page_count} pages")
                        if pdf_page_count != image_count:
                            print(f"  └─ ⚠️ Page count mismatch! Images: {image_count}, PDF pages: {pdf_page_count}")
                            report['mismatched_page_counts'].append({
                                'pdf_path': expected_pdf,
                                'pdf_pages': pdf_page_count,
                                'image_count': image_count,
                                'folder_path': root,
                                'image_types': [t.value for t in image_types_present] if has_multiple_types else [img_type.value]
                            })
                        else:
                            print("  └─ ✅ Page count matches")
                            
                except Exception as e:
                    error_msg = str(e)
                    print(f"  └─ ❌ PDF error: {error_msg}")
                    report['erroneous_pdfs'].append({
                        'path': expected_pdf,
                        'error': error_msg
                    })
            else:
                print(f"  └─ ❌ PDF not found: {os.path.basename(expected_pdf)}")
                report['folders_missing_pdf'].append({
                    'source': root,
                    'expected_pdf': expected_pdf,
                    'image_count': image_count,
                    'image_types': [t.value for t in image_types_present] if has_multiple_types else [img_type.value]
                })
                report['folders_missing_pdf_count'] += 1
        else:
            print("  └─ No matching images found")
    
    # Calculate total processing time
    report['processing_time_seconds'] = round(time.time() - start_time, 2)
    
    report['matching_status'] = (
        report['folders_with_images'] == report['total_pdf_count'] and 
        len(report['mismatched_page_counts']) == 0
    )
    
    # Print summary report
    print("\n📊 Summary Report:")
    print(f"Processing time: {report['processing_time_seconds']} seconds")
    print(f"Total folders scanned: {report['total_folder_count']}")
    print(f"Folders with images: {report['folders_with_images']}")
    print(f"Total images found: {report['total_image_count']}")
    print(f"PDFs found: {report['total_pdf_count']}")
    print(f"Missing PDFs: {report['folders_missing_pdf_count']}")
    print(f"PDFs with page count mismatch: {len(report['mismatched_page_counts'])}")
    print(f"PDFs with errors: {len(report['erroneous_pdfs'])}")
    print(f"Folders with multiple image types: {len(report['multi_type_folders'])}")
    print(f"Overall status: {'✅ All good' if report['matching_status'] else '❌ Issues found'}")
    
    if report['image_type_stats']:
        print("\nImage type statistics:")
        for img_type, stats in report['image_type_stats'].items():
            print(f"- {img_type}:")
            print(f"  ├─ Total images: {stats['count']}")
            print(f"  └─ Found in {stats['folders']} folders")
    
    if report['multi_type_folders']:
        print("\nFolders with multiple image types:")
        for item in report['multi_type_folders']:
            print(f"- {item['path']}")
            print(f"  Types: {', '.join(item['types'])}")
    
    if report['folders_missing_pdf']:
        print("\nMissing PDFs:")
        for item in report['folders_missing_pdf']:
            types_str = f" ({', '.join(item['image_types'])})" if len(item['image_types']) > 1 else ""
            print(f"- {item['source']}{types_str} ({item['image_count']} images)")
    
    if report['mismatched_page_counts']:
        print("\nPage count mismatches:")
        for item in report['mismatched_page_counts']:
            types_str = f" ({', '.join(item['image_types'])})" if len(item['image_types']) > 1 else ""
            print(f"- {item['folder_path']}{types_str}: Images: {item['image_count']}, PDF pages: {item['pdf_pages']}")
    
    if report['erroneous_pdfs']:
        print("\nPDF errors:")
        for item in report['erroneous_pdfs']:
            print(f"- {item['path']}: {item['error']}")
    
    # Print JSON format
    print_json_report(report)
    
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
        'image_types_found': list(image_types) if image_types else [],
        'alreadyExists': []
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
        
        pdf_path = f"{output_path}.pdf"
        
        # Check if PDF already exists
        if os.path.exists(pdf_path):
            print(f"  ⚠️ PDF already exists: {os.path.basename(pdf_path)}")
            result['alreadyExists'].append(pdf_path)
            # Clean up loaded images
            for img in images:
                img.close()
            return result
            
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

@router.post("/verfiyImgtoPdf")
def verfiyImgtoPdf_route(request: FolderAnalysisRequest):
    folder_path = request.folder_path
    dest_folder = request.dest_folder
    
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="Source folder path does not exist")
        
    if not os.path.isdir(folder_path):
        raise HTTPException(status_code=400, detail="Source path must be a directory")
        
    if not os.path.exists(dest_folder):
        raise HTTPException(status_code=404, detail="Destination folder path does not exist")
        
    if not os.path.isdir(dest_folder):
        raise HTTPException(status_code=400, detail="Destination path must be a directory")
    
    try:
        report = verfiyImgtoPdf(folder_path, dest_folder, request.img_type)
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
