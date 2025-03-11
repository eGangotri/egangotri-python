import os
import time
import json
from enum import Enum
from typing import List, Dict, Set, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from PyPDF2 import PdfReader
import fitz
from PIL import Image
import rawpy
import glob
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from src.utils.image_constants import ImageType, get_extensions_for_type

router = APIRouter()

class FolderAnalysisRequest(BaseModel):
    src_folder: str
    dest_folder: Optional[str] = None
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
        'processing_time_seconds': report['processing_time_seconds'],
        'stats': {
            'total_folders': report['total_folder_count'],
            'folders_with_images': report['folders_with_images'],
            'total_images': report['total_image_count'],
            'pdfs_verified': report['total_pdf_count'],
            'folders_missing_pdf': report['folders_missing_pdf_count']
        },
        'image_type_stats': report['image_type_stats'],
        'issues': {
            'folders_with_mismatch_pages': [
                {
                    'folder': item['folder_path'],
                    'image_count': item['image_count'],
                    'pdf_pages': item['pdf_pages'],
                    'image_types': item['image_types']
                } for item in report['folders_with_mismatch_pages']
            ],
            'erroneous_pdfs': [
                {
                    'path': item['path'],
                    'error': item['error']
                } for item in report['erroneous_pdfs']
            ],
            'missing_pdfs': [
                {
                    'source': item['source'],
                    'expected_pdf': item['expected_pdf'],
                    'image_count': item['image_count'],
                    'image_types': item['image_types']
                } for item in report['folders_missing_pdf']
            ]
        },
        'multi_type_folders': [
            {
                'folder': item['path'],
                'image_types': item['types']
            } for item in report['multi_type_folders']
        ]
    }
    print("\n[*] JSON Report:")
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
        'image_type_filter': img_type,
        'folders_missing_pdf': [],
        'multi_type_folders': [],
        'processing_time_seconds': 0,
        'image_type_stats': {},
        'folders_with_mismatch_pages': [],  # Add list to track page count mismatches
        'folders_with_mismatch_pages_count': 0  # Count of folders with mismatches
    }
    
    print(f"\n[*] Starting verification...")
    print(f"Source path: {src_path}")
    print(f"Destination path: {dest_path}")
    print(f"Image type filter: {img_type.value}\n")
    
    # First count total processable folders
    total_folders = sum(1 for root, _, _ in os.walk(src_path) 
                      if not os.path.basename(root).startswith('.') and 
                      has_image_files(root, img_type))
    
    current_folder = 0
    for root, dirs, files in os.walk(src_path):
        if os.path.basename(root).startswith('.'):
            continue
            
        # Check for images of specified type
        if not has_image_files(root, img_type):
            continue
            
        current_folder += 1
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
            print(f"Processing folder ({current_folder}/{total_folders}): {rel_path} (Multiple image types: {', '.join(t.value for t in image_types_present)})")
        else:
            print(f"Processing folder ({current_folder}/{total_folders}): {rel_path}")
        
        # Check for images of specified type in source directory
        has_images = has_image_files(root, img_type)
        if has_images:
            report['folders_with_images'] += 1
            image_count = count_images_in_folder(root, img_type)
            report['total_image_count'] += image_count
            print(f"  [*] Found {image_count} images{' (filtered by type)' if has_multiple_types else ''}")
            
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
                        print(f"  [*] Found PDF with {pdf_page_count} pages")
                        if pdf_page_count != image_count:
                            print(f"  [X] Page count mismatch! Images: {image_count}, PDF pages: {pdf_page_count}")
                            report['folders_with_mismatch_pages'].append({
                                'pdf_path': expected_pdf,
                                'pdf_pages': pdf_page_count,
                                'image_count': image_count,
                                'folder_path': root,
                                'image_types': [t.value for t in image_types_present] if has_multiple_types else [img_type.value]
                            })
                            report['folders_with_mismatch_pages_count'] += 1
                        else:
                            print("  [*] Page count matches")
                            
                except Exception as e:
                    error_msg = str(e)
                    print(f"  [X] PDF error: {error_msg}")
                    report['erroneous_pdfs'].append({
                        'path': expected_pdf,
                        'error': error_msg
                    })
            else:
                print(f"  [-] PDF not found: {os.path.basename(expected_pdf)}")
                report['folders_missing_pdf'].append({
                    'source': root,
                    'expected_pdf': expected_pdf,
                    'image_count': image_count,
                    'image_types': [t.value for t in image_types_present] if has_multiple_types else [img_type.value]
                })
                report['folders_missing_pdf_count'] += 1
        else:
            print("  [-] No matching images found")
    
    # Calculate total processing time
    report['processing_time_seconds'] = time.time() - start_time
    
    print(f"\n[*] Verification completed in {report['processing_time_seconds']:.2f} seconds")
    
    report['matching_status'] = (
        report['folders_with_images'] == report['total_pdf_count'] and 
        len(report['folders_with_mismatch_pages']) == 0
    )
    
    # Print summary report
    print("\n[*] Summary Report:")
    print(f"Time taken: {report['processing_time_seconds']} seconds")
    print(f"Total folders scanned: {report['total_folder_count']}")
    print(f"Folders with images: {report['folders_with_images']}")
    print(f"Total images found: {report['total_image_count']}")
    print(f"PDFs found: {report['total_pdf_count']}")
    print(f"Missing PDFs: {report['folders_missing_pdf_count']}")
    print(f"PDFs with page count mismatch: {len(report['folders_with_mismatch_pages'])}")
    print(f"PDFs with errors: {len(report['erroneous_pdfs'])}")
    print(f"Folders with multiple image types: {len(report['multi_type_folders'])}")
    print(f"Overall status: {'[*] All good' if report['matching_status'] else '[X] Issues found'}")
    
    if report['image_type_stats']:
        print("\n[*] Image type statistics:")
        for img_type, stats in report['image_type_stats'].items():
            print(f"- {img_type}:")
            print(f"  [*] Total images: {stats['count']}")
            print(f"  [*] Found in {stats['folders']} folders")
    
    if report['multi_type_folders']:
        print("\n[*] Folders with multiple image types:")
        for item in report['multi_type_folders']:
            print(f"- {item['path']}")
            print(f"  [*] Types: {', '.join(item['types'])}")
    
    if report['folders_missing_pdf']:
        print("\n[-] Missing PDFs:")
        for item in report['folders_missing_pdf']:
            types_str = f" ({', '.join(item['image_types'])})" if len(item['image_types']) > 1 else ""
            print(f"- {os.path.basename(item['source'])}{types_str} ({item['image_count']} images)")
    
    if report['folders_with_mismatch_pages']:
        print("\n[*] Page count mismatches:")
        for item in report['folders_with_mismatch_pages']:
            types_str = f" ({', '.join(item['image_types'])})" if len(item['image_types']) > 1 else ""
            print(f"- {os.path.basename(item['folder_path'])}{types_str}: Images: {item['image_count']}, PDF pages: {item['pdf_pages']}")
    
    if report['erroneous_pdfs']:
        print("\n[X] PDF errors:")
        for item in report['erroneous_pdfs']:
            print(f"- {os.path.basename(item['path'])}: {item['error']}")
    
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

def process_images_to_pdf(folder_path: str, output_path: str, img_type: ImageType, image_types: set = None, folder_index: int = None, total_folders: int = None) -> dict:
    """Process images in a folder and convert them to a PDF."""
    result = {
        'success': False,
        'error': None,
        'pdf_path': None,
        'skipped': False,
        'image_count': 0
    }
    
    try:
        folder_name = os.path.basename(folder_path)
        pdf_path = os.path.join(output_path, f"{folder_name}.pdf")
        
        # Skip if PDF already exists
        if os.path.exists(pdf_path):
            result['success'] = True
            result['pdf_path'] = pdf_path
            result['skipped'] = True
            print(f"  Skipping existing PDF: {os.path.basename(pdf_path)}")
            return result
            
        folder_progress = f"({folder_index}/{total_folders})" if folder_index is not None and total_folders is not None else ""
        print(f"Creating PDF{folder_progress}: {os.path.basename(pdf_path)}")
        
        # Get list of images
        images = []
        extensions = get_extensions_for_type(img_type)
        for file in sorted(os.listdir(folder_path)):
            if file.lower().endswith(tuple(extensions)):
                images.append(os.path.join(folder_path, file))
        
        if not images:
            result['error'] = "No matching images found"
            return result
            
        result['image_count'] = len(images)
        
        # Create PDF
        doc = fitz.open()
        for i, img_path in enumerate(images, 1):
            print(f"Adding image {i}/{len(images)} to PDF(folder_{folder_index}/{total_folders}): {os.path.basename(img_path)}")
            
            try:
                img = Image.open(img_path)
                
                # Handle transparency for PNG files
                if img_path.lower().endswith('.png') and img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, 'white')
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[3])
                    else:
                        background.paste(img, mask=img.split()[1])
                    img = background
                
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save as temporary JPEG
                temp_jpg = os.path.join(os.path.dirname(img_path), f"temp_{os.path.basename(img_path)}.jpg")
                img.save(temp_jpg, 'JPEG', quality=95)
                
                # Add to PDF
                page = doc.new_page(width=img.width, height=img.height)
                page.insert_image(page.rect, filename=temp_jpg)
                
                # Clean up temp file
                os.remove(temp_jpg)
                
            except Exception as e:
                print(f"  [X] Error processing image {os.path.basename(img_path)}: {str(e)}")
                continue
        
        # Save PDF
        doc.save(pdf_path)
        doc.close()
        
        result['success'] = True
        result['pdf_path'] = pdf_path
        print(f"  PDF created successfully with {len(images)} pages")
        
    except Exception as e:
        result['error'] = str(e)
        print(f"  [X] Error creating PDF: {str(e)}")
    
    return result

@router.post("/verfiyImgtoPdf")
def verfiyImgtoPdf_route(request: FolderAnalysisRequest):
    src_folder = request.src_folder
    dest_folder = request.dest_folder
    
    if not os.path.exists(src_folder):
        raise HTTPException(status_code=404, detail="Source folder path does not exist")
        
    if not os.path.isdir(src_folder):
        raise HTTPException(status_code=400, detail="Source path must be a directory")
        
    if dest_folder and not os.path.exists(dest_folder):
        raise HTTPException(status_code=404, detail="Destination folder path does not exist")
        
    if dest_folder and not os.path.isdir(dest_folder):
        raise HTTPException(status_code=400, detail="Destination path must be a directory")
    
    try:
        report = verfiyImgtoPdf(src_folder, dest_folder, request.img_type)
        
        # Print final report summary
        print("\n[*] Verification Summary:")
        print(f"Time taken: {report['processing_time_seconds']:.2f} seconds")
        print(f"Total folders checked: {report['total_folder_count']}")
        print(f"Folders with images: {report['folders_with_images']}")
        print(f"Total images found: {report['total_image_count']}")
        print(f"PDFs verified: {report['total_pdf_count']}")
        
        if report['folders_with_mismatch_pages']:
            print("\n[*] Page count mismatches:")
            for mismatch in report['folders_with_mismatch_pages']:
                print(f"- {os.path.basename(mismatch['folder_path'])}")
                print(f"  Images: {mismatch['image_count']}, PDF pages: {mismatch['pdf_pages']}")
        
        if report['erroneous_pdfs']:
            print("\n[X] PDF errors:")
            for pdf in report['erroneous_pdfs']:
                print(f"- {os.path.basename(pdf['path'])}: {pdf['error']}")
        
        if report['folders_missing_pdf']:
            print("\n[-] Missing PDFs:")
            for folder in report['folders_missing_pdf']:
                print(f"- {os.path.basename(folder['source'])}")
        
        if report['image_type_stats']:
            print("\n[*] Image Type Statistics:")
            for img_type, stats in report['image_type_stats'].items():
                print(f"- {img_type}:")
                print(f"  Count: {stats['count']} images in {stats['folders']} folders")
        
        # Convert paths to relative paths in the report for JSON serialization
        if report['folders_with_mismatch_pages']:
            for item in report['folders_with_mismatch_pages']:
                item['folder_path'] = os.path.relpath(item['folder_path'], src_folder)
                item['pdf_path'] = os.path.relpath(item['pdf_path'], dest_folder or src_folder)
        
        if report['erroneous_pdfs']:
            for item in report['erroneous_pdfs']:
                item['path'] = os.path.relpath(item['path'], dest_folder or src_folder)
        
        if report['folders_missing_pdf']:
            for item in report['folders_missing_pdf']:
                item['source'] = os.path.relpath(item['source'], src_folder)
                item['expected_pdf'] = os.path.relpath(item['expected_pdf'], dest_folder or src_folder)
        
        return report
    except Exception as e:
        print(f"\n[X] Error during verification: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/convert-img-folder-to-pdf")
def process_img_folder_to_pdf_route(request: FolderAnalysisRequest):
    """Process a folder and convert images to PDFs."""
    start_time = time.time()
    
    # Initialize report
    report = {
        'total_folders': 0,
        'folders_with_images': 0,
        'pdfs_created': 0,
        'pdfs_skipped': 0,
        'processed_folders': [],
        'multi_type_folders': [],
        'errors': [],
        'error_count': 0,
        'failed_images_count': 0,
        'successful_images_count': 0,
        'time_taken_seconds': 0,
        'pdf_count_matches_folders': False,
        'error_types': {}
    }
    
    try:
        print("\nScanning folders...")
        
        # Create destination folder if it doesn't exist
        if request.dest_folder and not os.path.exists(request.dest_folder):
            print(f"Creating destination folder: {request.dest_folder}")
            os.makedirs(request.dest_folder)
            
        # First count total processable folders
        total_folders = sum(1 for root, _, _ in os.walk(request.src_folder) 
                          if not os.path.basename(root).startswith('.') and 
                          any(has_image_files(root, img_type) for img_type in [request.img_type]))
        
        current_folder = 0
        for root, dirs, files in os.walk(request.src_folder):
            try:
                if os.path.basename(root).startswith('.'):
                    continue
                    
                # Check for images of the specified type
                if not has_image_files(root, request.img_type):
                    continue
                    
                current_folder += 1
                report['total_folders'] += 1
                
                # Determine output path
                if request.dest_folder:
                    rel_path = os.path.relpath(root, request.src_folder)
                    pdf_base_path = os.path.join(request.dest_folder, rel_path)
                    # Create destination subfolder if needed
                    if not os.path.exists(pdf_base_path):
                        print(f"Processing folder ({current_folder}/{total_folders}): {rel_path}")
                        os.makedirs(pdf_base_path)
                else:
                    pdf_base_path = root
                    
                # Get all image types in the folder
                image_types = get_image_types_in_folder(root)
                
                if len(image_types) > 1:
                    print(f"\nProcessing folder ({current_folder}/{total_folders}): {rel_path}")
                    print(f"Multiple image types found: {', '.join(t.value for t in image_types)}")
                    report['multi_type_folders'].append({
                        'folder': root,
                        'types': [t.value for t in image_types]
                    })
                    
                try:
                    result = process_images_to_pdf(root, pdf_base_path, request.img_type, image_types, 
                                                 folder_index=current_folder, total_folders=total_folders)
                    
                    if result['success']:
                        if result['skipped']:
                            report['pdfs_skipped'] += 1
                        else:
                            report['pdfs_created'] += 1
                            report['successful_images_count'] += result['image_count']
                            report['failed_images_count'] += 0  # No failed images tracked in this version
                            
                        folder_result = {
                            'folder': root,
                            'pdfs': [result['pdf_path']],
                            'image_types': [t.value for t in image_types],
                            'images_processed': result['image_count'],
                            'images_failed': 0  # No failed images tracked in this version
                        }
                        
                        report['processed_folders'].append(folder_result)
                        
                    else:
                        error_msg = result['error']
                        print(f"[X] Error in folder {rel_path}: {error_msg}")
                        
                        report['errors'].append({
                            'folder': root,
                            'error': error_msg
                        })
                        report['error_count'] += 1
                        report['failed_images_count'] += 0  # No failed images tracked in this version
                        
                except Exception as e:
                    error_msg = f"Error processing folder: {str(e)}"
                    print(f"[X] Error in folder {rel_path}: {error_msg}")
                    
                    report['errors'].append({
                        'folder': root,
                        'error': error_msg
                    })
                    report['error_count'] += 1
                    continue
                    
            except Exception as e:
                error_msg = f"Unexpected error processing folder: {str(e)}"
                print(f"[X] Error in folder {rel_path if 'rel_path' in locals() else root}: {error_msg}")
                
                report['errors'].append({
                    'folder': root,
                    'error': error_msg
                })
                report['error_count'] += 1
                continue
    
    except Exception as e:
        error_msg = f"Critical error during folder processing: {str(e)}"
        print(f"[X] {error_msg}")
        
        report['errors'].append({
            'error': error_msg
        })
        report['error_count'] += 1
        return report
    
    # Calculate final statistics
    report['time_taken_seconds'] = time.time() - start_time
    report['pdf_count_matches_folders'] = report['pdfs_created'] == report['folders_with_images']
    
    # Print final report
    print("\n[*] Final Report:")
    print(f"Time taken: {report['time_taken_seconds']:.2f} seconds")
    print(f"Total folders processed: {report['total_folders']}")
    print(f"Folders with images: {report['folders_with_images']}")
    print(f"PDFs created: {report['pdfs_created']}")
    print(f"PDFs skipped: {report['pdfs_skipped']}")
    print(f"Images processed: {report['successful_images_count']}")
    print(f"Images failed: {report['failed_images_count']}")
    print(f"Total errors encountered: {report['error_count']}")
    print(f"Status: {'[*] Success' if report['pdf_count_matches_folders'] else '[X] Some folders may have failed'}")
    print(f"Multi-type folders: {len(report['multi_type_folders'])}")
    
    if report['errors']:
        print(f"\n[X] Errors ({report['error_count']}):")
        for error in report['errors']:
            if 'folder' in error:
                print(f"- {error['folder']}: {error['error']}")
            else:
                print(f"- {error['error']}")
    
    return report
