import os
import time
import logging
from fastapi import APIRouter, HTTPException
import fitz
from src.utils.image_constants import ImageType
from .utils import (
    FolderAnalysisRequest,
    has_image_files,
    count_images_in_folder,
    get_image_types_in_folder,
    print_json_report
)

router = APIRouter()

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
    processing_time = time.time() - start_time
    report['processing_time_seconds'] = processing_time
    
    print(f"\n[*] Verification completed in {processing_time:.2f} seconds")
    
    # Safely calculate matching status
    folders_with_images = report.get('folders_with_images', 0)
    total_pdf_count = report.get('total_pdf_count', 0)
    mismatch_pages = report.get('folders_with_mismatch_pages', [])
    
    report['matching_status'] = (
        folders_with_images == total_pdf_count and 
        len(mismatch_pages) == 0
    )
    
    # Print summary report with safe access
    print("\n[*] Summary Report:")
    print(f"Time taken: {processing_time:.2f} seconds")
    print(f"Total folders scanned: {report.get('total_folder_count', 0)}")
    print(f"Folders with images: {folders_with_images}")
    print(f"Total images found: {report.get('total_image_count', 0)}")
    print(f"PDFs found: {total_pdf_count}")
    print(f"Missing PDFs: {report.get('folders_missing_pdf_count', 0)}")
    print(f"PDFs with page count mismatch: {len(mismatch_pages)}")
    print(f"PDFs with errors: {len(report.get('erroneous_pdfs', []))}")
    print(f"Folders with multiple image types: {len(report.get('multi_type_folders', []))}")
    print(f"Overall status: {'[*] All good' if report.get('matching_status', False) else '[X] Issues found'}")
    
    if report.get('image_type_stats'):
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
        print(f"Time taken: {report.get('processing_time_seconds', 0):.2f} seconds")
        print(f"Total folders checked: {report.get('total_folder_count', 0)}")
        print(f"Folders with images: {report.get('folders_with_images', 0)}")
        print(f"Total images found: {report.get('total_image_count', 0)}")
        print(f"PDFs verified: {report.get('total_pdf_count', 0)}")
        
        if report.get('folders_with_mismatch_pages', []):
            print("\n[*] Page count mismatches:")
            for mismatch in report.get('folders_with_mismatch_pages', []):
                print(f"- {os.path.basename(mismatch['folder_path'])}")
                print(f"  Images: {mismatch['image_count']}, PDF pages: {mismatch['pdf_pages']}")
        
        if report.get('erroneous_pdfs', []):
            print("\n[X] PDF errors:")
            for pdf in report.get('erroneous_pdfs', []):
                print(f"- {os.path.basename(pdf['path'])}: {pdf['error']}")
        
        if report.get('folders_missing_pdf', []):
            print("\n[-] Missing PDFs:")
            for folder in report.get('folders_missing_pdf', []):
                print(f"- {os.path.basename(folder['source'])}")
        
        if report.get('image_type_stats', {}):
            print("\n[*] Image Type Statistics:")
            for img_type, stats in report.get('image_type_stats', {}).items():
                print(f"- {img_type}:")
                print(f"  Count: {stats['count']} images in {stats['folders']} folders")
        
        # Convert paths to relative paths in the report for JSON serialization
        if report.get('folders_with_mismatch_pages', []):
            for item in report.get('folders_with_mismatch_pages', []):
                item['folder_path'] = os.path.relpath(item['folder_path'], src_folder)
                item['pdf_path'] = os.path.relpath(item['pdf_path'], dest_folder or src_folder)
        
        if report.get('erroneous_pdfs', []):
            for item in report.get('erroneous_pdfs', []):
                item['path'] = os.path.relpath(item['path'], dest_folder or src_folder)
        
        if report.get('folders_missing_pdf', []):
            for item in report.get('folders_missing_pdf', []):
                item['source'] = os.path.relpath(item['source'], src_folder)
                item['expected_pdf'] = os.path.relpath(item['expected_pdf'], dest_folder or src_folder)
        
        return report
    except Exception as e:
        print(f"\n[X] Error during verification: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
