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
        
        # Get original file size for comparison
        original_size = os.path.getsize(input_pdf) / (1024 * 1024)  # Size in MB
        
        # Try more aggressive compression settings
        compression_level = '/screen'  # Options: /screen (smallest), /ebook, /printer, /prepress (highest quality)
        
        print(f"Attempting Ghostscript compression with level {compression_level}")
        print(f"Original size: {original_size:.2f} MB")
        
        # Run ghostscript with selected compression settings
        subprocess.run([
            gs_command, 
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            f'-dPDFSETTINGS={compression_level}',
            '-dNOPAUSE',
            '-dQUIET',
            '-dBATCH',
                    f'-sOutputFile={output_pdf}',
                    input_pdf
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Verify the output file exists and check size difference
        if os.path.exists(output_pdf):
            compressed_size = os.path.getsize(output_pdf) / (1024 * 1024)  # Size in MB
            size_reduction = original_size - compressed_size
            percent_reduction = (size_reduction / original_size) * 100 if original_size > 0 else 0
            
            print(f"Compressed size: {compressed_size:.2f} MB")
            print(f"Size reduction: {size_reduction:.2f} MB ({percent_reduction:.1f}%)")
            
            if compressed_size < original_size:
                print(f" Compression successful")
                return True
            else:
                print(f" Compression did not reduce file size (possibly already optimized)")
                # If compression didn't help, use the original file
                if input_pdf != output_pdf:  # Avoid copying to self
                    shutil.copy(input_pdf, output_pdf)
                return False
        
        return False
    except Exception as e:
        print(f" Ghostscript compression failed: {str(e)}")
        # Try to check if Ghostscript is installed and accessible
        try:
            version_check = subprocess.run([gs_command, '--version'], 
                                          stdout=subprocess.PIPE, 
                                          stderr=subprocess.PIPE, 
                                          text=True)
            print(f"Ghostscript version: {version_check.stdout.strip()}")
        except:
            print(" Ghostscript may not be installed or not in PATH")
        
        return False
