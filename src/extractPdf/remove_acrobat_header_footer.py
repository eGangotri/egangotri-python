import fitz  # PyMuPDF
import pikepdf
import re
import os
import sys
from datetime import datetime
from typing import Dict, Optional

def remove_acrobat_headers_footers(input_pdf, output_pdf=None):
    """
    Surgically removes Adobe Acrobat Headers and Footers.
    
    Args:
        input_pdf (str): Path to the input PDF file.
        output_pdf (str, optional): Path to the output PDF file. If None, it appends '_cleaned' to the original name.
    """
    if not output_pdf:
        base, ext = os.path.splitext(input_pdf)
        output_pdf = f"{base}_cleaned{ext}"

    temp_structural = f"{input_pdf}.temp_structural.pdf"

    try:
        # --- Step 1: Structural Cleaning with pikepdf ---
        # This removes the metadata that makes Acrobat "see" these as headers/footers.
        print(f"Opening {input_pdf} for structural cleaning...")
        with pikepdf.open(input_pdf) as pdf:
            found_piece_info = False
            for page in pdf.pages:
                # Remove PieceInfo which stores Adobe's Header/Footer settings
                if "/PieceInfo" in page:
                    del page["PieceInfo"]
                    found_piece_info = True
            
            if not found_piece_info:
                print("Note: No Adobe PieceInfo metadata found. The file might not have Acrobat-managed headers/footers.")
                
            pdf.save(temp_structural)

        # --- Step 2: Content Stream Cleaning with PyMuPDF (fitz) ---
        # This removes the actual drawing instructions from the content stream.
        print(f"Cleaning content streams...")
        with fitz.open(temp_structural) as doc:
            # Regex to match Acrobat's Header/Footer Artifact blocks.
            # Acrobat uses /Artifact << /Type /Pagination /Subtype /Header ... >> BDC ... EMC
            artifact_pattern = re.compile(
                rb'\/Artifact\s*<<[^>]*?\/Subtype\s*\/(Header|Footer)[^>]*?>>\s*BDC.*?EMC', 
                re.DOTALL
            )

            cleaned_count = 0
            for page in doc:
                # Get all content streams for the page
                contents = page.get_contents()
                for xref in contents:
                    stream_data = doc.xref_stream(xref)
                    
                    # Remove the matching Artifact blocks
                    new_data = artifact_pattern.sub(b'', stream_data)
                    
                    if new_data != stream_data:
                        doc.update_stream(xref, new_data)
                        cleaned_count += 1
                        
            # Step 3: Finalize and Save
            doc.save(output_pdf, garbage=4, deflate=True, clean=True)
        
        print(f"Successfully processed {input_pdf}")
        if cleaned_count > 0:
            print(f"Removed {cleaned_count} header/footer content blocks.")
        print(f"Cleaned PDF saved as: {output_pdf}")

    except Exception as e:
        print(f"Error during removal: {str(e)}")
    finally:
        # Cleanup temp file
        if os.path.exists(temp_structural):
            try:
                os.remove(temp_structural)
            except Exception as cleanup_error:
                print(f"Note: Could not delete temporary file {temp_structural}: {cleanup_error}")

def process_folder_remove_headers_footers(input_folder: str, output_folder: Optional[str] = None) -> Dict:
    """
    Recursively processes all PDF files in input_folder to remove Acrobat headers/footers.
    Maintains folder hierarchy in output_folder.
    """
    start_time = datetime.now()
    
    if not os.path.exists(input_folder):
        raise ValueError(f"Input path '{input_folder}' does not exist")

    default_output = output_folder if output_folder else (os.path.dirname(input_folder) if os.path.isfile(input_folder) else input_folder)
    
    stats = {
        "totalFiles": 0,
        "processedFiles": 0,
        "errors": 0,
        "input_folder": input_folder,
        "output_folder": default_output,
        "log_messages": [],
        "start_time": start_time.isoformat(),
        "duration_seconds": 0.0,
        "processing_details": []
    }

    pdf_files = []
    if os.path.isfile(input_folder):
        if input_folder.lower().endswith('.pdf'):
            pdf_files.append((os.path.dirname(input_folder), os.path.basename(input_folder)))
            # For a single file, we override the input_folder base for os.path.relpath calculation
            search_root = os.path.dirname(input_folder)
        else:
            raise ValueError(f"'{input_folder}' is not a PDF file")
    else:
        search_root = input_folder
        for root, dirs, files in os.walk(input_folder):
            for file in files:
                if file.lower().endswith('.pdf'):
                    # Avoid processing already cleaned files in the same run if in-place
                    if not file.lower().endswith('_cleaned.pdf'):
                        pdf_files.append((root, file))

    stats["totalFiles"] = len(pdf_files)
    msg = f"🔍 Found {len(pdf_files)} PDF file(s) to process at {input_folder}"
    print(msg)
    stats["log_messages"].append(msg)

    for idx, (root, file) in enumerate(pdf_files, 1):
        input_pdf = os.path.join(root, file)
        
        # Calculate output path
        if output_folder:
            relative_path = os.path.relpath(root, search_root)
            target_dir = os.path.join(output_folder, relative_path)
            os.makedirs(target_dir, exist_ok=True)
            output_pdf = os.path.join(target_dir, file)
        else:
            output_pdf = None 

        msg = f"⏳ [{idx}/{len(pdf_files)}] Processing: {file}"
        print(msg)
        stats["log_messages"].append(msg)
        
        try:
            # We could get page count here if we wanted to be perfectly matches
            # but for now let's focus on successful removal
            remove_acrobat_headers_footers(input_pdf, output_pdf)
            stats["processedFiles"] += 1
            
            success_msg = f"✅ Successfully processed {file}"
            stats["log_messages"].append(success_msg)
            
            stats["processing_details"].append({
                "file": file,
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

    stats["duration_seconds"] = (datetime.now() - start_time).total_seconds()
    
    summary = [
        f"📊 Bulk Processing Summary:",
        f"   • Total Files: {stats['totalFiles']}",
        f"   • Successfully Cleaned: {stats['processedFiles']}",
        f"   • Errors: {stats['errors']}",
        f"   • Time Taken: {stats['duration_seconds']:.2f}s"
    ]
    stats["log_messages"].extend(summary)
    
    return stats

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python remove_acrobat_header_footer.py <input_pdf> [output_pdf]")
    else:
        in_file = sys.argv[1]
        out_file = sys.argv[2] if len(sys.argv) > 2 else None
        remove_acrobat_headers_footers(in_file, out_file)
