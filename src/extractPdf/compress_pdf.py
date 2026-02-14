import os
import subprocess
import shutil
import glob

def _find_ghostscript():
    """
    Tries to find Ghostscript executable in common installation paths.
    Returns the path to the executable or just the name if it's in PATH.
    """
    # 1. Check if GHOSTSCRIPT_PATH is set in environment
    env_gs_path = os.environ.get('GHOSTSCRIPT_PATH')
    if env_gs_path and os.path.exists(env_gs_path):
        return env_gs_path

    # 2. Check if it's already in PATH
    gs_exe = 'gswin64c.exe' if os.name == 'nt' else 'gs'
    if shutil.which(gs_exe):
        return gs_exe
    
    if os.name == 'nt':
        # 2. Check common installation paths on Windows
        common_paths = [
            r"C:\Program Files\gs\gs*\bin\gswin64c.exe",
            r"C:\Program Files (x86)\gs\gs*\bin\gswin64c.exe",
        ]
        for pattern in common_paths:
            matches = glob.glob(pattern)
            if matches:
                # Use the latest version if multiple are found
                matches.sort(reverse=True)
                return matches[0]
                
    return gs_exe # Fallback to default name

def _compress_with_ghostscript(input_pdf, output_pdf):
    """
    Uses Ghostscript for better PDF compression if available.
    Returns True if successful, False otherwise.
    """
    try:
        # Resolve absolute paths and normalize
        input_pdf = os.path.abspath(input_pdf)
        output_pdf = os.path.abspath(output_pdf)
        
        # Check if ghostscript is available
        gs_command = _find_ghostscript()
        
        if not os.path.exists(input_pdf):
            print(f" Error: Input file for compression not found: {input_pdf}")
            return False
            
        # Get original file size for comparison
        original_size = os.path.getsize(input_pdf) / (1024 * 1024)  # Size in MB
        
        # Try more aggressive compression settings
        compression_level = '/screen'  # Options: /screen (smallest), /ebook, /printer, /prepress (highest quality)
        
        print(f"Attempting Ghostscript compression with level {compression_level}")
        print(f"Using Ghostscript at: {gs_command}")
        print(f"Original size: {original_size:.2f} MB")
        
        # Run ghostscript with selected compression settings
        result = subprocess.run([
            gs_command, 
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            f'-dPDFSETTINGS={compression_level}',
            '-dNOPAUSE',
            '-dQUIET',
            '-dBATCH',
            f'-sOutputFile={output_pdf}',
            input_pdf
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
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
    except subprocess.CalledProcessError as e:
        print(f" Ghostscript process failed: {e.stderr}")
        return False
    except Exception as e:
        print(f" Ghostscript compression failed: {str(e)}")
        # Try to check if Ghostscript is installed and accessible
        try:
            gs_command = _find_ghostscript()
            version_check = subprocess.run([gs_command, '--version'], 
                                          stdout=subprocess.PIPE, 
                                          stderr=subprocess.PIPE, 
                                          text=True)
            print(f"Ghostscript version check: {version_check.stdout.strip()}")
        except:
            print(" Ghostscript may not be installed or correctly configured in PATH")
        
        return False

