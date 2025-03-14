import fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter
import os
import subprocess
import shutil

def _compress_with_ghostscript(input_pdf, output_pdf):
    """
    Uses Ghostscript for better PDF compression if available.
    Returns True if successful, False otherwise.
    """
    try:
        # Check if ghostscript is available
        gs_command = 'gswin64c' if os.name == 'nt' else 'gs'
        
        # Try to run ghostscript with aggressive compression settings
        subprocess.run([
            gs_command, 
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            '-dPDFSETTINGS=/ebook',  # Options: /screen, /ebook, /printer, /prepress
            '-dNOPAUSE',
            '-dQUIET',
            '-dBATCH',
            f'-sOutputFile={output_pdf}',
            input_pdf
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Verify the output file exists and is smaller
        if os.path.exists(output_pdf) and os.path.getsize(output_pdf) < os.path.getsize(input_pdf):
            return True
            
        return False
    except Exception as e:
        print(f"Ghostscript compression failed: {str(e)}")
        return False
