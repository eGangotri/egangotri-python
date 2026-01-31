import fitz  # PyMuPDF
import pikepdf
import re
import os
import sys

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

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python remove_acrobat_header_footer.py <input_pdf> [output_pdf]")
    else:
        in_file = sys.argv[1]
        out_file = sys.argv[2] if len(sys.argv) > 2 else None
        remove_acrobat_headers_footers(in_file, out_file)
