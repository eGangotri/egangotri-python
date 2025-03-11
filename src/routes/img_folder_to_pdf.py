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
        'mismatched_page_counts': [],
        'image_type_filter': img_type,
        'folders_missing_pdf': [],
        'multi_type_folders': [],
        'processing_time_seconds': 0,
        'image_type_stats': {}
    }
    
    print(f"\n[*] Starting verification...")
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
                            print(f"  └─ [X] Page count mismatch! Images: {image_count}, PDF pages: {pdf_page_count}")
                            report['mismatched_page_counts'].append({
                                'pdf_path': expected_pdf,
                                'pdf_pages': pdf_page_count,
                                'image_count': image_count,
                                'folder_path': root,
                                'image_types': [t.value for t in image_types_present] if has_multiple_types else [img_type.value]
                            })
                        else:
                            print("  └─ [*] Page count matches")
                            
                except Exception as e:
                    error_msg = str(e)
                    print(f"  └─ [X] PDF error: {error_msg}")
                    report['erroneous_pdfs'].append({
                        'path': expected_pdf,
                        'error': error_msg
                    })
            else:
                print(f"  └─ [X] PDF not found: {os.path.basename(expected_pdf)}")
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
    print("\n[*] Summary Report:")
    print(f"Processing time: {report['processing_time_seconds']} seconds")
    print(f"Total folders scanned: {report['total_folder_count']}")
    print(f"Folders with images: {report['folders_with_images']}")
    print(f"Total images found: {report['total_image_count']}")
    print(f"PDFs found: {report['total_pdf_count']}")
    print(f"Missing PDFs: {report['folders_missing_pdf_count']}")
    print(f"PDFs with page count mismatch: {len(report['mismatched_page_counts'])}")
    print(f"PDFs with errors: {len(report['erroneous_pdfs'])}")
    print(f"Folders with multiple image types: {len(report['multi_type_folders'])}")
    print(f"Overall status: {'[*] All good' if report['matching_status'] else '[X] Issues found'}")
    
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

def process_images_to_pdf(folder_path: str, output_path: str, img_type: ImageType, image_types: set = None, folder_index: int = None, total_folders: int = None) -> dict:
    """Process images in a folder and convert them to a PDF."""
    result = {
        'success': False,
        'pdf_path': None,
        'error': None,
        'error_type': None,
        'images_processed': 0,
        'images_failed': 0,
        'failed_images': [],
        'skipped': False
    }
    
    try:
        # Get the folder name for the PDF name
        folder_name = os.path.basename(folder_path)
        
        # Get all image files in the folder
        images = []
        for ext in get_extensions_for_type(img_type):
            images.extend(glob.glob(os.path.join(folder_path, f"*.{ext}")))
        images.sort()  # Sort images to ensure consistent order
        
        if not images:
            result['error'] = 'No matching images found'
            result['error_type'] = 'no_images'
            return result
            
        # Create output directory if it doesn't exist
        try:
            os.makedirs(output_path, exist_ok=True)
        except Exception as e:
            result['error'] = f"Failed to create output directory: {str(e)}"
            result['error_type'] = 'directory_creation_error'
            return result
        
        # Determine PDF path based on image types
        if image_types and len(image_types) > 1:
            # If multiple types, append the specific type to PDF name
            pdf_path = os.path.join(output_path, f"{folder_name}_{img_type.value}.pdf")
        else:
            pdf_path = os.path.join(output_path, f"{folder_name}.pdf")
        
        # Skip if PDF already exists
        if os.path.exists(pdf_path):
            result['success'] = True
            result['pdf_path'] = pdf_path
            result['skipped'] = True
            print(f"  Skipping existing PDF: {os.path.basename(pdf_path)}")
            return result
            
        folder_progress = f"({folder_index}/{total_folders})" if folder_index is not None and total_folders is not None else ""
        print(f"  Creating PDF{folder_progress}: {os.path.basename(pdf_path)}")
        
        # Create PDF
        try:
            c = canvas.Canvas(pdf_path, pagesize=letter)
            
            # Process each image
            for i, img_path in enumerate(images, 1):
                try:
                    print(f"    Adding image {i}/{len(images)} to PDF{folder_progress}...")
                    
                    # Handle different image types
                    if img_path.lower().endswith('.cr2'):
                        try:
                            with rawpy.imread(img_path) as raw:
                                rgb = raw.postprocess()
                                img = Image.fromarray(rgb)
                        except Exception as e:
                            print(f"    [X] Error processing CR2 image {os.path.basename(img_path)}: {str(e)}")
                            result['images_failed'] += 1
                            result['failed_images'].append({
                                'path': img_path,
                                'error': str(e),
                                'error_type': 'cr2_processing_error'
                            })
                            continue
                    else:
                        try:
                            img = Image.open(img_path)
                        except Exception as e:
                            print(f"    [X] Error opening image {os.path.basename(img_path)}: {str(e)}")
                            result['images_failed'] += 1
                            result['failed_images'].append({
                                'path': img_path,
                                'error': str(e),
                                'error_type': 'image_open_error'
                            })
                            continue
                    
                    try:
                        # Convert RGBA to RGB if necessary (add white background)
                        if img.mode == 'RGBA':
                            background = Image.new('RGB', img.size, 'white')
                            background.paste(img, mask=img.split()[3])
                            img = background
                        
                        # Convert to RGB if not already
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        # Calculate dimensions to fit on the page
                        img_width, img_height = img.size
                        aspect = img_height / float(img_width)
                        
                        # Set page dimensions
                        if aspect > 1:
                            # Portrait
                            page_width = letter[0] - 40
                            page_height = page_width * aspect
                        else:
                            # Landscape
                            page_height = letter[1] - 40
                            page_width = page_height / aspect
                        
                        # Add the image to the PDF
                        c.setPageSize((page_width + 40, page_height + 40))
                        c.drawImage(ImageReader(img), 20, 20, width=page_width, height=page_height)
                        c.showPage()
                        result['images_processed'] += 1
                        
                    except Exception as e:
                        print(f"    [X] Error adding image {os.path.basename(img_path)} to PDF: {str(e)}")
                        result['images_failed'] += 1
                        result['failed_images'].append({
                            'path': img_path,
                            'error': str(e),
                            'error_type': 'pdf_addition_error'
                        })
                        continue
                        
                except Exception as e:
                    print(f"    [X] Unexpected error processing image {os.path.basename(img_path)}: {str(e)}")
                    result['images_failed'] += 1
                    result['failed_images'].append({
                        'path': img_path,
                        'error': str(e),
                        'error_type': 'unexpected_image_error'
                    })
                    continue
            
            # Save the PDF if we processed any images successfully
            if result['images_processed'] > 0:
                try:
                    c.save()
                    result['success'] = True
                    result['pdf_path'] = pdf_path
                    if result['images_failed'] > 0:
                        result['error'] = f"PDF created with {result['images_failed']} failed images"
                        result['error_type'] = 'partial_success'
                except Exception as e:
                    result['error'] = f"Failed to save PDF: {str(e)}"
                    result['error_type'] = 'pdf_save_error'
            else:
                result['error'] = "No images were successfully processed"
                result['error_type'] = 'all_images_failed'
            
        except Exception as e:
            result['error'] = f"Failed to create PDF: {str(e)}"
            result['error_type'] = 'pdf_creation_error'
            
    except Exception as e:
        result['error'] = f"Unexpected error: {str(e)}"
        result['error_type'] = 'unexpected_error'
    
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
        return report
    except Exception as e:
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
                
                # Calculate relative path to maintain directory structure
                rel_path = os.path.relpath(root, request.src_folder)
                
                # Create corresponding path in destination
                if request.dest_folder:
                    pdf_base_path = os.path.join(request.dest_folder, rel_path)
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
                            report['successful_images_count'] += result['images_processed']
                            report['failed_images_count'] += result['images_failed']
                        
                        folder_result = {
                            'folder': root,
                            'pdfs': [result['pdf_path']],
                            'image_types': [t.value for t in image_types],
                            'images_processed': result['images_processed'],
                            'images_failed': result['images_failed']
                        }
                        
                        if result['error_type'] == 'partial_success':
                            folder_result['partial_success'] = True
                            folder_result['failed_images'] = result['failed_images']
                            # Track error type statistics
                            for failed_image in result['failed_images']:
                                error_type = failed_image['error_type']
                                if error_type not in report['error_types']:
                                    report['error_types'][error_type] = 0
                                report['error_types'][error_type] += 1
                        
                        report['processed_folders'].append(folder_result)
                        
                    else:
                        error_msg = result['error']
                        error_type = result['error_type']
                        print(f"[X] Error in folder {rel_path}: {error_msg}")
                        
                        # Track error type statistics
                        if error_type not in report['error_types']:
                            report['error_types'][error_type] = 0
                        report['error_types'][error_type] += 1
                        
                        report['errors'].append({
                            'folder': root,
                            'error': error_msg,
                            'error_type': error_type,
                            'failed_images': result.get('failed_images', [])
                        })
                        report['error_count'] += 1
                        report['failed_images_count'] += result.get('images_failed', 0)
                        
                except Exception as e:
                    error_msg = f"Error processing folder: {str(e)}"
                    print(f"[X] Error in folder {rel_path}: {error_msg}")
                    
                    error_type = 'processing_error'
                    if error_type not in report['error_types']:
                        report['error_types'][error_type] = 0
                    report['error_types'][error_type] += 1
                    
                    report['errors'].append({
                        'folder': root,
                        'error': error_msg,
                        'error_type': error_type
                    })
                    report['error_count'] += 1
                    continue
                    
            except Exception as e:
                error_msg = f"Unexpected error processing folder: {str(e)}"
                print(f"[X] Error in folder {rel_path if 'rel_path' in locals() else root}: {error_msg}")
                
                error_type = 'unexpected_error'
                if error_type not in report['error_types']:
                    report['error_types'][error_type] = 0
                report['error_types'][error_type] += 1
                
                report['errors'].append({
                    'folder': root,
                    'error': error_msg,
                    'error_type': error_type
                })
                report['error_count'] += 1
                continue
    
    except Exception as e:
        error_msg = f"Critical error during folder processing: {str(e)}"
        print(f"[X] {error_msg}")
        
        error_type = 'critical_error'
        if error_type not in report['error_types']:
            report['error_types'][error_type] = 0
        report['error_types'][error_type] += 1
        
        report['errors'].append({
            'error': error_msg,
            'error_type': error_type
        })
        report['error_count'] += 1
        return report
    
    # Calculate final statistics
    report['time_taken_seconds'] = round(time.time() - start_time, 2)
    report['pdf_count_matches_folders'] = report['pdfs_created'] == report['folders_with_images']
    
    # Print final report
    print("\n[*] Conversion Process Summary:")
    print(f"Time taken: {report['time_taken_seconds']} seconds")
    print(f"Total folders processed: {report['total_folders']}")
    print(f"Folders with images: {report['folders_with_images']}")
    print(f"PDFs created: {report['pdfs_created']}")
    print(f"PDFs skipped (already exist): {report['pdfs_skipped']}")
    print(f"Images successfully processed: {report['successful_images_count']}")
    print(f"Images failed: {report['failed_images_count']}")
    print(f"Multi-type folders: {len(report['multi_type_folders'])}")
    print(f"Total errors encountered: {report['error_count']}")
    print(f"Status: {'[*] Success' if report['pdf_count_matches_folders'] else '[X] Some folders may have failed'}")
    
    if report['error_types']:
        print("\nError Type Statistics:")
        for error_type, count in report['error_types'].items():
            print(f"- {error_type.replace('_', ' ').title()}: {count}")
    
    if report['multi_type_folders']:
        print("\nFolders with multiple image types:")
        for folder in report['multi_type_folders']:
            print(f"- {folder['folder']}")
            print(f"  Types: {', '.join(folder['types'])}")
    
    if report['errors']:
        print(f"\nErrors ({report['error_count']}):")
        error_types = {}
        for error in report['errors']:
            error_type = error.get('error_type', 'unknown')
            if error_type not in error_types:
                error_types[error_type] = []
            error_types[error_type].append(error)
        
        for error_type, errors in error_types.items():
            print(f"\n{error_type.replace('_', ' ').title()} ({len(errors)}):")
            for error in errors:
                if 'folder' in error:
                    print(f"- {error['folder']}: {error['error']}")
                    if 'failed_images' in error and error['failed_images']:
                        for img_error in error['failed_images']:
                            print(f"  └─ {os.path.basename(img_error['path'])}: {img_error['error']}")
                else:
                    print(f"- {error['error']}")
    
    return report
