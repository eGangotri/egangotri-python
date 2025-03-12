import fitz  # PyMuPDF
import os
import argparse
import json
from typing import List, Dict
from fastapi import HTTPException
from datetime import datetime

REDUCED_FOLDER = 'reduced'


def extract_first_and_last_n_pages(input_pdf: str, output_pdf: str, firstN: int = 10, lastN: int = 10) -> None:
    doc = fitz.open(input_pdf)
    new_doc = fitz.open()

    try:
        # Extract first N pages
        for i in range(min(firstN, len(doc))):
            new_doc.insert_pdf(doc, from_page=i, to_page=i)

        # Extract last N pages
        for i in range(max(0, len(doc) - lastN), len(doc)):
            new_doc.insert_pdf(doc, from_page=i, to_page=i)

        new_doc.save(output_pdf)
    finally:
        new_doc.close()
        doc.close()


def process_pdfs_in_folder(input_folder: str, output_folder: str = None, firstN: int = 10, lastN: int = 10) -> Dict:
    start_time = datetime.now()
    
    # Initialize statistics with default output folder
    default_output = os.path.join(input_folder, REDUCED_FOLDER) if output_folder is None else output_folder
    
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
        raise HTTPException(status_code=400, detail="Input folder path cannot be empty")
    if not os.path.exists(input_folder):
        raise HTTPException(status_code=400, detail=f"Input folder '{input_folder}' does not exist")
    if not os.path.isdir(input_folder):
        raise HTTPException(status_code=400, detail=f"'{input_folder}' is not a directory")

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
        stats["duration_seconds"] = (datetime.now() - start_time).total_seconds()
        return stats

    # Setup output folder with count
    last_folder_name = os.path.basename(os.path.normpath(input_folder))
    folder_with_count = f"{last_folder_name}({stats['totalFiles']})"
    
    final_output = os.path.join(default_output, folder_with_count)
    stats["output_folder"] = final_output
    os.makedirs(final_output, exist_ok=True)

    # Process files with detailed progress reporting
    msg = f"📂 Found {stats['totalFiles']} PDF files in {input_folder}"
    print(msg)
    stats["log_messages"].append(msg)

    for idx, (root, file) in enumerate(pdf_files, 1):
        try:
            input_pdf = os.path.join(root, file)
            doc = fitz.open(input_pdf)
            page_count = len(doc)
            doc.close()

            base_name, ext = os.path.splitext(file)
            new_file_name = f"{base_name}_{page_count:04d}{ext}"

            # Maintain the original folder structure
            relative_path = os.path.relpath(root, input_folder)
            output_subfolder = os.path.join(final_output, relative_path)
            os.makedirs(output_subfolder, exist_ok=True)
            output_pdf = os.path.join(output_subfolder, new_file_name)

            # Progress message before processing
            msg = f"⏳ ({idx}/{stats['totalFiles']}) Processing: {file} ({page_count} pages)"
            print(msg)
            stats["log_messages"].append(msg)

            extract_first_and_last_n_pages(input_pdf, output_pdf, firstN, lastN)
            stats["processedFiles"] += 1
            
            # Success message
            msg = f"✅ ({idx}/{stats['totalFiles']}) Completed: {file} -> {new_file_name}"
            print(msg)
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

    args = parser.parse_args()
    result = process_pdfs_in_folder(args.input_folder, args.output_folder, args.firstN, args.lastN)
    print(json.dumps(result, indent=4))
