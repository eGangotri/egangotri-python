"""Module for extracting and combining first and last N pages from PDF files.

This module provides functionality to:
- Extract a specified number of pages from the beginning and end of PDF files
- Process multiple PDFs in a directory
- Optionally compress the resulting PDFs using ghostscript
- Support both PyPDF2 and PyMuPDF (fallback) for PDF processing
"""

import os
import argparse
import json
from typing import Dict, Optional
from datetime import datetime
from fastapi import HTTPException
from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF 1.26.0

from src.extractPdf.compress_pdf import _compress_with_ghostscript

REDUCED_FOLDER = 'reduced'
# Suffix for temporary files during processing
TEMP_SUFFIX = "_temp"

def extract_first_and_last_n_pages(input_pdf: str, 
                        output_pdf: str, firstN: int = 10, lastN: int = 10, 
                        reduce_size: bool = True, commonRunId: Optional[str] = None,
                        runId: Optional[str] = None, compression_level: Optional[str] = None ) -> None:
    """Extract first and last N pages from a PDF, with size reduction options."""
    
    # We'll use a temporary path for the extraction if we plan to compress it later
    extraction_target = output_pdf
    if reduce_size:
        base, ext = os.path.splitext(output_pdf)
        extraction_target = f"{base}_temp_extract{ext}"

    # Try PyPDF2 for extraction
    success = False
    try:
        print(f"Using PyPDF2 for extraction: {os.path.basename(input_pdf)}")
        success = _extract_with_pypdf2(input_pdf, extraction_target, firstN, lastN, reduce_size, commonRunId, runId)
    except Exception as e:
        print(f"PyPDF2 approach failed, falling back to PyMuPDF: {str(e)}")
        success = _extract_with_pymupdf(input_pdf, extraction_target, firstN, lastN, reduce_size, commonRunId, runId)

    if not success:
        raise Exception("Failed to extract pages from PDF")

    # Apply Ghostscript compression if requested
    if reduce_size:
        print(f"Applying Ghostscript compression to {os.path.basename(output_pdf)}...")
        compression_success = _compress_with_ghostscript(extraction_target, output_pdf, compression_level)
        
        # Clean up the temporary extraction file
        if os.path.exists(extraction_target):
            try:
                os.remove(extraction_target)
            except Exception as e:
                print(f"Warning: Could not remove temporary file {extraction_target}: {str(e)}")
        
        if not compression_success:
            print("Ghostscript compression was not successful or not available. Using extracted version.")
            if not os.path.exists(output_pdf): # If _compress didn't even create the output
                import shutil
                shutil.copy(extraction_target, output_pdf)
    
    return True


def _extract_with_pypdf2(input_pdf, output_pdf, firstN, lastN, reduce_size, commonRunId: Optional[str] = None,
runId: Optional[str] = None ):
    """Extract and compress using PyPDF2 library with more aggressive settings."""
    with open(input_pdf, 'rb') as file:
        reader = PdfReader(file)
        writer = PdfWriter()

        total_pages = len(reader.pages)
        print(f"Total pages in original PDF: {total_pages}")

        # Calculate pages to include
        first_indices = range(min(firstN, total_pages))
        last_indices = range(max(0, total_pages - lastN), total_pages)
        selected = set(list(first_indices) + list(last_indices))
        selected = sorted(list(selected))

        print(f"Selected {len(selected)} pages from {total_pages} total pages")

        # Add selected pages to the new PDF
        for i in selected:
            writer.add_page(reader.pages[i])

        # Apply compression if requested
        if reduce_size:
            print("Applying PDF compression to improve file size...")
            # Activate compression on every page
            # for page in writer.pages:
            #     page.compress_content_streams()  # This applies compression to content streams

            # # Set the compression parameters for the writer
            # writer.remove_images = False  # Keep images but compress them

        # Write the output file
        with open(output_pdf, 'wb') as output_file:
            writer.write(output_file)

        # Return success
        return True


def _extract_with_pymupdf(input_pdf, output_pdf, firstN, lastN, reduce_size, commonRunId: Optional[str] = None,
runId: Optional[str] = None ):
    """Extract using PyMuPDF as a fallback method."""
    doc = fitz.open(input_pdf)  # Updated to use open() instead of Document()
    total_pages = len(doc)

    # Calculate pages to include
    first_indices = range(min(firstN, total_pages))
    last_indices = range(max(0, total_pages - lastN), total_pages)
    selected = set(list(first_indices) + list(last_indices))
    selected = sorted(list(selected))

    # Create a new document with selected pages
    new_doc = fitz.open()  # Updated to use open() instead of Document()
    for i in selected:
        new_doc.insert_pdf(doc, from_page=i, to_page=i)

    print(
        f"Selected {len(selected)} pages from {total_pages} total pages using PyMuPDF")

    if reduce_size:
        # Basic compression settings
        print('Saving with PyMuPDF basic compression...')
        new_doc.save(output_pdf, garbage=4, deflate=True)
    else:
        new_doc.save(output_pdf)

    new_doc.close()
    doc.close()
    return True


def process_pdfs_in_folder(input_folder: str, 
output_folder: str = None, firstN: int = 10, lastN: int = 10,
 reduce_size: bool = True,
 commonRunId: Optional[str] = None,
 runId: Optional[str] = None, compression_level: Optional[str] = None) -> Dict:
    """Process multiple PDF files in a folder by extracting first and last N pages.

    Args:
        input_folder (str): Path to the folder containing input PDF files
        output_folder (str, optional): Path to save output files. If None, creates 'reduced' subfolder in input_folder
        firstN (int, optional): Number of pages to extract from start of each PDF. Defaults to 10
        lastN (int, optional): Number of pages to extract from end of each PDF. Defaults to 10
        reduce_size (bool, optional): Whether to compress output PDFs. Defaults to True

    Returns:
        Dict: Statistics about the processing including:
            - totalFiles: Number of PDF files found
            - processedFiles: Number of files successfully processed
            - errors: Number of files that failed processing
            - duration_seconds: Total processing time
            - output_folder: Path where output files were saved
            - log_messages: List of processing status messages
            - processing_details: Per-file processing information

    Raises:
        HTTPException: If input_folder doesn't exist or other processing errors occur
    """
    start_time = datetime.now()

    # Initialize statistics with default output folder
    # If output_folder is provided, use it directly. Otherwise, use '<input_folder>/reduced'
    default_output = output_folder if output_folder is not None else os.path.join(input_folder, REDUCED_FOLDER)

    stats = {
        "totalFiles": 0,
        "processedFiles": 0,
        "errors": 0,
        "input_folder": input_folder,
        "output_folder": default_output,  # Set initial default
        "log_messages": [],
        "start_time": start_time.isoformat(),
        "duration_seconds": 0.0,
        "processing_details": []
    }

    # Input validation with detailed messages
    if not input_folder:
        raise HTTPException(
            status_code=400, detail="Input folder path cannot be empty")
    if not os.path.exists(input_folder):
        raise HTTPException(
            status_code=400, detail=f"Input folder '{input_folder}' does not exist")
    if not os.path.isdir(input_folder):
        raise HTTPException(
            status_code=400, detail=f"'{input_folder}' is not a directory")

    # Find PDF files with progress reporting
    msg = f"🔍 Scanning {input_folder} for PDF files..."
    print(msg)
    stats["log_messages"].append(msg)

    pdf_files = []
    for root, dirs, files in os.walk(input_folder):
        # Ignore any subfolder named "reduced"
        dirs[:] = [d for d in dirs if d.lower() != REDUCED_FOLDER]
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append((root, file))

    stats["totalFiles"] = len(pdf_files)

    # Early return if no PDFs found
    if stats["totalFiles"] == 0:
        msg = f"📂 No PDF files found in {input_folder}"
        print(msg)
        stats["log_messages"].append(msg)
        stats["duration_seconds"] = (
            datetime.now() - start_time).total_seconds()
        return stats

    # Setup output folder
    # Only append '<last_folder_name>(count)' when using the default reduced folder.
    # If a custom output_folder is provided, do NOT append the input folder name to avoid duplication.
    last_folder_name = os.path.basename(os.path.normpath(input_folder))
    folder_with_count = f"{last_folder_name}({stats['totalFiles']})"

    if output_folder is None:
        final_output = os.path.join(default_output, folder_with_count)
    else:
        final_output = default_output
    stats["output_folder"] = final_output
    os.makedirs(final_output, exist_ok=True)

    # Process files with detailed progress reporting
    msg = f"📂 Found {stats['totalFiles']} PDF files in {input_folder}"
    print(msg)
    stats["log_messages"].append(msg)

    for idx, (root, file) in enumerate(pdf_files, 1):
        try:
            input_pdf = os.path.join(root, file)
            try:
                doc = fitz.open(input_pdf)
                page_count = len(doc)
                doc.close()
            except Exception as e:
                print(
                    f"Warning: Could not read page count for {file}: {str(e)}")
                page_count = 0  # Default if we can't read it

            base_name, ext = os.path.splitext(file)
            new_file_name = f"{base_name}_{page_count:04d}{ext}"

            # Maintain the original folder structure
            relative_path = os.path.relpath(root, input_folder)
            if relative_path == ".":
                output_subfolder = final_output
            else:
                output_subfolder = os.path.join(final_output, relative_path)
                
            output_subfolder = os.path.normpath(output_subfolder)
            os.makedirs(output_subfolder, exist_ok=True)
            output_pdf = os.path.join(output_subfolder, new_file_name)
            output_pdf = os.path.normpath(output_pdf)

            # Progress message before processing
            msg = f"⏳ ({idx}/{stats['totalFiles']}) Processing: {file} ({page_count} pages)"
            print(msg)
            stats["log_messages"].append(msg)

            try:
                extract_first_and_last_n_pages(
                    input_pdf, output_pdf, firstN, lastN, 
                    reduce_size, commonRunId, runId, compression_level)
                stats["processedFiles"] += 1

                # Success message with size info
                original_size = os.path.getsize(
                    input_pdf) / (1024 * 1024)  # Convert to MB
                new_size = os.path.getsize(
                    output_pdf) / (1024 * 1024)  # Convert to MB
                size_info = f" (Old Size: {original_size:.2f} MB, New Size: {new_size:.2f} MB)"
                msg = f"✅ ({idx}/{stats['totalFiles']}) Completed: {file} -> {new_file_name}{size_info}"
                print(msg)

            except Exception as e:
                error_msg = f"❌ Error extracting pages from {file}: {str(e)}"
                print(error_msg)
                stats["log_messages"].append(error_msg)
                raise  # Re-raise to be caught by the outer try-except

            stats["log_messages"].append(msg)

            # Add processing details
            stats["processing_details"].append({
                "file": file,
                "original_pages": page_count,
                "pages_extracted": min(firstN, page_count) + min(lastN, page_count),
                "status": "success"
            })

        except Exception as e:
            error_msg = f"❌ Error processing {file}: {str(e)}"
            print(error_msg)
            stats["log_messages"].append(error_msg)
            stats["errors"] += 1
            stats["processing_details"].append({
                "file": file,
                "status": "error",
                "error": str(e)
            })

    # Add final summary with emojis
    end_time = datetime.now()
    stats["duration_seconds"] = (end_time - start_time).total_seconds()
    print("PDF Reduction Script completed after processing {idx}/{stats['totalFiles']} at {end_time}")
    summary = [
        f"📊 Processing Summary:",
        f"   • Total Files: {stats['totalFiles']}",
        f"   • Processed Successfully: {stats['processedFiles']}",
        f"   • Errors: {stats['errors']}",
        f"   • Processing Time: {stats['duration_seconds']:.2f} seconds",
        f"   • Input Folder: {input_folder}",
        f"   • Output Folder: {stats['output_folder']}"
    ]

    stats["log_messages"].extend(summary)
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract first and last N pages from PDFs in a folder.")
    parser.add_argument(
        "input_folder", help="The input folder containing PDF files.")
    parser.add_argument("--output_folder",
                        help="The output folder to save reduced PDF files.")
    parser.add_argument("--firstN", type=int, default=10,
                        help="Number of first pages to extract.")
    parser.add_argument("--lastN", type=int, default=10,
                        help="Number of last pages to extract.")
    parser.add_argument("--no-reduce-size", action="store_true",
                        help="Disable PDF size reduction (enabled by default)")
    parser.add_argument("--commonRunId", help="Common Run ID for tracking")
    parser.add_argument("--runId", help="Run ID for tracking")
    parser.add_argument("--compression-level", help="Ghostscript compression level (e.g., screen, ebook)")

    args = parser.parse_args()
    result = process_pdfs_in_folder(
        args.input_folder, args.output_folder, args.firstN, args.lastN, not args.no_reduce_size, args.commonRunId, args.runId, args.compression_level)
    print(json.dumps(result, indent=4))
