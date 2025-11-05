import os
import time
import psutil
import logging
from fastapi import APIRouter, HTTPException
from src.config import API_ENDPOINTS
from src.utils.image_constants import ImageType, get_extensions_for_type
from .utils import (
    FolderAnalysisRequest,
    has_image_files,
    get_image_types_in_folder,
    create_pdf_from_images
)
import requests
router = APIRouter()

def process_images_to_pdf(folder_path: str, output_path: str, img_type: ImageType, image_types: set = None, folder_index: int = None, total_folders: int = None) -> dict:
    """Process images in a folder and convert them to a PDF."""
    result = {
        'success': False,
        'error': None,
        'pdf_path': None,
        'skipped': False,
        'image_count': 0,
        'pdf_page_count': 0,
        'pages_match_images': False,
    }
    
    try:
        folder_name = os.path.basename(folder_path)
        # Ensure output directory exists
        os.makedirs(output_path, exist_ok=True)
        
        pdf_path = os.path.normpath(os.path.join(output_path, f"{folder_name}.pdf"))
        logging.info("PDF will be created at: %s", pdf_path)
        
        # Skip if PDF already exists
        if os.path.exists(pdf_path):
            result['success'] = True
            result['pdf_path'] = pdf_path
            result['skipped'] = True
            logging.info("Skipping existing PDF: %s", os.path.basename(pdf_path))
            return result
            
        folder_progress = f"({folder_index}/{total_folders})" if folder_index is not None and total_folders is not None else ""
        logging.info("Creating PDF%s: %s", folder_progress, os.path.basename(pdf_path))
        
        # Get list of images
        images = []
        extensions = get_extensions_for_type(img_type)
        for file in sorted(os.listdir(folder_path)):
            if file.lower().endswith(tuple(ext.lower() for ext in extensions)):
                images.append(os.path.join(folder_path, file))
        
        if not images:
            result['error'] = "No matching images found"
            return result
        
        # Create PDF from images
        pdf_result = create_pdf_from_images(images, folder_name, output_path)
        
        # Update result with PDF creation status
        if not pdf_result['success']:
            result['folderError'] = pdf_result['folderError']
            return result
        
        # Copy all relevant fields from pdf_result
        result.update({
            'success': True,
            'pdf_path': pdf_path,
            'image_count': len(images),
            'pdf_page_count': pdf_result.get('pdf_page_count', 0),
            'pages_match_images': pdf_result.get('pages_match_images', False)
        })
        
        logging.info("Created PDF %s with %d pages", pdf_path, result['pdf_page_count'])
        
        if result['success']:
            logging.info("PDF created successfully with %s pages", len(images))
        else:
            logging.error("Failed to create PDF: %s", result.get('error', 'Unknown error'))

    except Exception as e:
        result['error'] = str(e)
        if folder_index is not None and total_folders is not None:
            logging.error("Error creating PDF(%d/%d): %s", folder_index, total_folders, str(e))
        else:
            logging.error("Error creating PDF: %s", str(e))
    
    return result


def update_mongo_report(mongo_id: str, report: dict) -> bool:
    """Update the MongoDB document with the latest report status."""
    if not mongo_id:
        logging.warning("Cannot update MongoDB: No document ID available")
        return False
        
    try:
        response = requests.post(
            API_ENDPOINTS['update_entry'],
            json={'id': mongo_id, 'report': report},
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        if response.ok:
            logging.info("Successfully updated MongoDB document: %s", mongo_id)
            return True
        else:
            logging.error("Failed to update MongoDB document %s: %s - %s", 
                         mongo_id, response.status_code, response.text)
            return False
    except Exception as e:
        logging.error("Error updating MongoDB document %s: %s", mongo_id, str(e))
        return False

@router.post("/convert-img-folder-to-pdf")
def process_img_folder_to_pdf_route(request: FolderAnalysisRequest):
    """Process a folder and convert images to PDFs."""
    logging.info("Starting PDF conversion with request: src=%s, dest=%s, img_type=%s", 
                request.src_folder, request.dest_folder, request.img_type)
    start_time = time.time()
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Initialize report
    report = {
        'commonRunId': request.commonRunId,
        'total_folders': 0,
        'folders_detail': [],  # Array of objects with detailed folder processing info
        'total_folders_including_empty': 0,
        'summary': {
            'folders_with_images': 0,
            'pdfs_created': 0,
            'pdfs_skipped': 0,
            'error_count': 0,
            'failed_images_count': 0,
            'successful_images_count': 0,
            'time_taken_seconds': 0
        },
        'memory_stats': {
            'initial_mb': initial_memory,
            'peak_mb': initial_memory,
            'final_mb': 0,
            'net_change_mb': 0
        },
        'mongo_doc_id': None,  # To store the MongoDB document ID
        'paths': {
            'source': os.path.abspath(request.src_folder),
            'destination': os.path.abspath(request.dest_folder) if request.dest_folder else os.path.abspath(request.src_folder)
        }
    }
    
    try:
        src_folder = report['paths']['source']
        dest_folder = report['paths']['destination'] or src_folder

        # Validate source folder
        if not os.path.exists(src_folder):
            raise HTTPException(status_code=404, detail="Source folder does not exist")
        if not os.path.isdir(src_folder):
            raise HTTPException(status_code=400, detail="Source path must be a directory")

        # Create destination folder if it doesn't exist and is different from source
        if dest_folder != src_folder:
            try:
                os.makedirs(dest_folder, exist_ok=True)
                logging.info("Destination folder ready: %s", dest_folder)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to create destination folder: {str(e)}")
            
        logging.info("Starting folder scan with src_folder: %s", src_folder)
        logging.info("Destination folder: %s", dest_folder)
        logging.info("Source folder exists: %s", os.path.exists(src_folder))
        logging.info("Source folder is directory: %s", os.path.isdir(src_folder))
        logging.info("Source folder contents: %s", os.listdir(src_folder) if os.path.exists(src_folder) else "<not accessible>")
        logging.info("\nScanning folders...")
        
        # First collect all folders and their details
        processable_folders = []
        total_folders_including_empty = 0
        try:
            for root, _, files in os.walk(src_folder):
                logging.info("Processing folder: %s", root)
                if os.path.basename(root).startswith('.'):
                    logging.info("Skipping hidden folder: %s", root)
                    continue

                abs_path = os.path.abspath(root)
                folder_info = {
                    'folder_path': abs_path,
                    'has_images': False,
                    'image_count': 0,
                    'pdf_generated': False,
                    'pdf_path': '',
                    'pdf_page_count': 0,
                    'pages_match_images': False,
                    'folderErrors': [],
                    'error_count': 0,
                    'status': 'pending',
                    'skipped': False
                }

                # Count images of requested type
                extensions = get_extensions_for_type(request.img_type)
                image_files = [f for f in files if any(f.lower().endswith(ext.lower()) for ext in extensions)]
                logging.info("Found %d images in folder: %s with extensions %s", len(image_files), abs_path, extensions)
                total_folders_including_empty += 1
                if image_files:
                    folder_info['has_images'] = True
                    folder_info['image_count'] = len(image_files)
                    processable_folders.append(folder_info)
        except Exception as e:
            logging.error("Error during folder walk: %s", str(e))
            raise HTTPException(status_code=500, detail=f"Failed to scan folders: {str(e)}")

        logging.info("Found %d processable folders", len(processable_folders))
        
        # Update report with folder details
        total_folders = len(processable_folders)
        report['total_folders'] = total_folders
        report['summary']['folders_with_images'] = sum(1 for f in processable_folders if f['has_images'])
        report['folders_detail'] = processable_folders
        report['total_folders_including_empty'] = total_folders_including_empty
        report['commonRunId'] = request.commonRunId
        logging.info("Starting PDF generation for %d folders", total_folders)
        
        # Send initial report data to the REST service
        try:
            logging.info("Sending report data to REST service")
            response = requests.post(
                API_ENDPOINTS['create_entry'],
                json=report,
                headers={'Content-Type': 'application/json'},
                timeout=30  # Add timeout to avoid hanging
            )
            if response.ok:
                response_data = response.json()
                if 'id' in response_data:
                    report['mongo_doc_id'] = response_data['id']
                    logging.info("Successfully stored MongoDB document ID: %s", report['mongo_doc_id'])
                else:
                    logging.warning("Response missing MongoDB document ID")
            else:
                logging.warning("Failed to send report data to REST service: %s - %s", response.status_code, response.text)
        except Exception as e:
            logging.error("Error sending report data to REST service: %s", str(e))

        current_folder = 0
        for root, dirs, files in os.walk(src_folder):
            try:
                if os.path.basename(root).startswith('.'):
                    continue
                
                # Track memory at start of folder processing
                mem_before = process.memory_info().rss / 1024 / 1024
                print(f"Memory for folder({current_folder}/{total_folders}): {mem_before:.1f}MB")
                
                # Check for images of the specified type
                if not has_image_files(root, request.img_type):
                    continue
                    
                current_folder += 1
                report['summary']['folders_with_images'] += 1
                
                # Determine output path
                if request.dest_folder:
                    # If we're at the source root, use dest_folder directly
                    if root == src_folder:
                        pdf_base_path = dest_folder
                    else:
                        # Get relative path from source folder
                        rel_path = os.path.relpath(root, src_folder)
                        pdf_base_path = os.path.join(dest_folder, rel_path)
                else:
                    pdf_base_path = root
                
                logging.info("PDF base path will be: %s", pdf_base_path)
                    
                # Create destination subfolder if needed
                if not os.path.exists(pdf_base_path):
                    print(f"Processing folder ({current_folder}/{total_folders}): {rel_path}")
                    os.makedirs(pdf_base_path, exist_ok=True)
                
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
                    result = process_images_to_pdf(
                        folder_path=root,
                        output_path=pdf_base_path,
                        img_type=request.img_type,
                        image_types=image_types,
                        folder_index=current_folder,
                        total_folders=total_folders
                    )
                    
                    # Update folder info in the report
                    folder_info = next(info for info in report['folders_detail'] if info['folder_path'] == os.path.abspath(root))
                    folder_info['pdf_path'] = result.get('pdf_path', '')
                    folder_info['pdf_page_count'] = result.get('pdf_page_count', 0)
                    folder_info['pages_match_images'] = folder_info['pdf_page_count'] == folder_info['image_count']
                    
                    if result['success']:
                        folder_info['pdf_generated'] = True
                        if result['skipped']:
                            folder_info['skipped'] = True
                            folder_info['status'] = 'skipped'   
                            report['summary']['pdfs_skipped'] += 1
                        else:
                            folder_info['status'] = 'success'
                            report['summary']['pdfs_created'] += 1
                        report['summary']['successful_images_count'] += result['image_count']
                        report['summary']['failed_images_count'] += 0  # No failed images tracked in this version
                        
                        # Update MongoDB with success status
                        update_mongo_report(report['mongo_doc_id'], report)
                            
                    else:
                        error_msg = result['error']
                        logging.error("Error in folder %s: %s", rel_path, error_msg)
                        
                        # Update folder info with error details
                        folder_info = next(info for info in report['folders_detail'] if info['folder_path'] == os.path.abspath(root))
                        folder_info['folderErrors'].append(error_msg)
                        folder_info['error_count'] += 1
                        folder_info['status'] = 'error'
                        report['summary']['error_count'] += 1
                        
                        # Update MongoDB with error status
                        update_mongo_report(report['mongo_doc_id'], report)
                except Exception as e:
                    error_msg = f"Error processing folder {root}: {str(e)}"
                    logging.error("Error: %s", error_msg)
                    
                    # Update folder info with error details
                    folder_info = next(info for info in report['folders_detail'] if info['folder_path'] == os.path.abspath(root))
                    folder_info['folderErrors'].append(error_msg)
                    folder_info['error_count'] += 1
                    folder_info['status'] = 'error'
                    
                    report['summary']['error_count'] += 1
                    
                    # Update MongoDB with error status
                    update_mongo_report(report['mongo_doc_id'], report)
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
        
        # Track memory after folder processing
        mem_after = process.memory_info().rss / 1024 / 1024
        mem_diff = mem_after - mem_before
        if abs(mem_diff) > 1:  # Only show significant changes (>1MB)
            print(f"Memory change for folder({current_folder}/{total_folders}): {mem_diff:+.1f}MB")
        
        # Update peak memory
        report['memory_stats']['peak_mb'] = max(report['memory_stats']['peak_mb'], mem_after)
    
    except Exception as e:
        error_msg = f"Critical error during folder processing: {str(e)}"
        print(f"[X] {error_msg}")
        
        report['errors'].append({
            'error': error_msg
        })
        report['error_count'] += 1
        return report
    
    # Update final memory stats
    final_memory = process.memory_info().rss / 1024 / 1024
    report['memory_stats'].update({
        'final_mb': final_memory,
        'net_change_mb': final_memory - initial_memory
    })
    
    print("\nMemory Usage Report:")
    print(f"[*] Initial Memory: {report['memory_stats']['initial_mb']:.1f}MB")
    print(f"[*] Peak Memory: {report['memory_stats']['peak_mb']:.1f}MB")
    print(f"[*] Final Memory: {report['memory_stats']['final_mb']:.1f}MB")
    print(f"[*] Total Memory Change: {report['memory_stats']['net_change_mb']:+.1f}MB")
    
    # Calculate final statistics
    report['time_taken_seconds'] = time.time() - start_time
    report['summary']['pdf_count_matches_folders'] = report['summary']['pdfs_created'] == report['summary']['folders_with_images']
    
    # Print final report
    print("\n[*] Final Report:")
    print(f"Time taken: {report.get('time_taken_seconds', 0):.2f} seconds")
    print(f"Total folders processed: {report.get('total_folders', 0)}")
    print(f"Total folders including empty: {report.get('total_folders_including_empty', 0)}")
    print(f"Folders with images: {report.get('folders_with_images', 0)}")
    print(f"PDFs created: {report.get('pdfs_created', 0)}")
    print(f"PDFs skipped: {report.get('pdfs_skipped', 0)}")
    print(f"Images processed: {report.get('successful_images_count', 0)}")
    print(f"Images failed: {report.get('failed_images_count', 0)}")
    print(f"Total errors encountered: {report.get('error_count', 0)}")
    print(f"Status: {'[*] Success' if report.get('pdf_count_matches_folders', False) else '[X] Some folders may have failed'}")
    print(f"Multi-type folders: {len(report.get('multi_type_folders', []))}")
    
    if report.get('errors', []):
        print(f"\n[X] Errors ({report.get('error_count', 0)}):")
        for error in report.get('errors', []):
            if 'folder' in error:
                print(f"- {error['folder']}: {error['error']}")
            else:
                print(f"- {error['error']}")
    
    return report
