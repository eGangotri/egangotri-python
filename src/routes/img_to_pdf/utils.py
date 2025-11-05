import os
import time
import json
import logging
from typing import Optional, Set
from pydantic import BaseModel
from PIL import Image
import fitz
from src.utils.image_constants import ImageType, get_extensions_for_type


class ImageConversionRequest(BaseModel):
    src_folder: str
    dest_folder: str
    img_type: ImageType = ImageType.ANY
    commonRunId: Optional[str] = None

class FolderAnalysisRequest(BaseModel):
    src_folder: str
    dest_folder: Optional[str] = None
    img_type: ImageType = ImageType.ANY
    commonRunId: Optional[str] = None


def has_image_files(folder_path: str, img_type: ImageType) -> bool:
    extensions = get_extensions_for_type(img_type)
    for file in os.listdir(folder_path):
        if any(file.lower().endswith(ext.lower()) for ext in extensions):
            return True
    return False

def count_images_in_folder(folder_path: str, img_type: ImageType) -> int:
    """Count the number of images of specified type in a folder."""
    count = 0
    extensions = get_extensions_for_type(img_type)
    for file in os.listdir(folder_path):
        if any(file.lower().endswith(ext.lower()) for ext in extensions):
            count += 1
    return count

def get_image_types_in_folder(folder_path: str) -> set:
    """Get all image types present in a folder."""
    image_types = set()
    for img_type in ImageType:
        if img_type != ImageType.ANY and has_image_files(folder_path, img_type):
            image_types.add(img_type)
    return image_types


def create_pdf_from_images(images: list, folder_name: str, output_path: str) -> dict:
    """Create a PDF from a list of images.
    
    Args:
        images: List of full paths to image files
        folder_name: Name of the folder (used for PDF title)
        output_path: Directory where to save the PDF and temp files
        
    Returns:
        dict with keys:
            success: bool
            error: Optional[str]
            pdf_path: Optional[str]
            image_count: int
    """
    result = {
        'success': False,
        'folderError': None,
        'pdf_path': None,
        'image_count': len(images),
        'pdf_page_count': 0,
        'pages_match_images': False,
    }
    
    try:
        # Create PDF file path
        pdf_path = os.path.join(output_path, f"{folder_name}.pdf")
        
        # Create PDF with metadata
        doc = fitz.open()
        doc.set_metadata({
            "creator": "Egangotri PDF Generator",
            "producer": "Fitz",
            "title": folder_name,
            "creationDate": fitz.get_pdf_now(),
            "modDate": fitz.get_pdf_now()
        })
        
        temp_files = []  # Track temp files for cleanup
        
        for i, img_path in enumerate(images, 1):
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
                
                # Save as temporary JPEG in the output directory
                temp_jpeg = os.path.join(output_path, f"temp_{i}.jpg")
                img.save(temp_jpeg, 'JPEG', quality=95)
                temp_files.append(temp_jpeg)
                
                # Add page to PDF
                doc.new_page(width=img.width, height=img.height)
                page = doc[-1]
                page.insert_image(page.rect, filename=temp_jpeg)
                
            except Exception as e:
                logging.error("Error processing image %s: %s", os.path.basename(img_path), str(e))
                continue
            
        # Save the PDF
        doc.save(pdf_path)
        page_count = len(doc)
        result.update({
            'success': True,
            'pdf_path': pdf_path,
            'pdf_page_count': page_count,
            'pages_match_images': len(images) == page_count
        })
        logging.info("Created PDF %s with %d pages, images: %d", 
                   os.path.basename(pdf_path), page_count, len(images))
        
    except Exception as e:
        result['folderError'] = str(e)
        logging.error("Error creating PDF: %s", str(e))
    
    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logging.error("Error removing temp file %s: %s", temp_file, str(e))
    
    return result


def print_json_report(report: dict):
    """Print the report in JSON format for machine consumption."""
    json_output = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'processing_time_seconds': report.get('processing_time_seconds', 0),
        'stats': {
            'total_folders': report.get('total_folder_count', 0),
            'total_folders_including_empty': report.get('total_folders_including_empty', 0),
            'folders_with_images': report.get('folders_with_images', 0),
            'total_images': report.get('total_image_count', 0),
            'pdfs_verified': report.get('total_pdf_count', 0),
            'folders_missing_pdf': report.get('folders_missing_pdf_count', 0)
        },
        'image_type_stats': report.get('image_type_stats', {}),
        'issues': {
            'folders_with_mismatch_pages': [
                {
                    'folder': item['folder_path'],
                    'image_count': item['image_count'],
                    'pdf_pages': item['pdf_page_count'],
                    'image_types': item['image_types']
                } for item in report.get('folders_with_mismatch_pages', [])
            ],
            'erroneous_pdfs': [
                {
                    'path': item['path'],
                    'error': item['error']
                } for item in report.get('erroneous_pdfs', [])
            ],
            'missing_pdfs': [
                {
                    'source': item['source'],
                    'expected_pdf': item['expected_pdf'],
                    'image_count': item['image_count'],
                    'image_types': item['image_types']
                } for item in report.get('folders_missing_pdf', [])
            ]
        },
        'multi_type_folders': [
            {
                'folder': item['path'],
                'image_types': item['types']
            } for item in report.get('multi_type_folders', [])
        ]
    }
    print("\n[*] JSON Report:")
    print(json.dumps(json_output, indent=2))
