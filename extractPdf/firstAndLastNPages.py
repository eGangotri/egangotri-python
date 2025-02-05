import fitz  # PyMuPDF
import os
import argparse

REDUCED_FOLDER = 'reduced'

def extract_first_and_last_n_pages(input_pdf, output_pdf, firstN=10, lastN=10):
    doc = fitz.open(input_pdf)
    new_doc = fitz.open()
    
    # Extract first N pages
    for i in range(min(firstN, len(doc))):
        new_doc.insert_pdf(doc, from_page=i, to_page=i)
    
    # Extract last N pages
    for i in range(max(0, len(doc) - lastN), len(doc)):
        new_doc.insert_pdf(doc, from_page=i, to_page=i)
    
    new_doc.save(output_pdf)
    new_doc.close()

def process_pdfs_in_folder(input_folder, output_folder=None, firstN=10, lastN=10):
    if output_folder is None:
        output_folder = os.path.join(input_folder, REDUCED_FOLDER)
    
    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    pdf_files = []
    for root, dirs, files in os.walk(input_folder):
        # Ignore any subfolder named "reduced"
        dirs[:] = [d for d in dirs if d.lower() != REDUCED_FOLDER]
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append((root, file))
    
    total_files = len(pdf_files)
    for count, (root, file) in enumerate(pdf_files, start=1):
        input_pdf = os.path.join(root, file)
        doc = fitz.open(input_pdf)
        page_count = len(doc)
        doc.close()
        
        base_name, ext = os.path.splitext(file)
        new_file_name = f"{base_name}_{page_count:04d}{ext}"
        
        output_subfolder = output_folder
        os.makedirs(output_subfolder, exist_ok=True)
        output_pdf = os.path.join(output_subfolder, new_file_name)
        
        extract_first_and_last_n_pages(input_pdf, output_pdf, firstN, lastN)
        print(f"{count}/{total_files}) {file} reduced to {firstN + lastN} pages as {new_file_name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract first and last N pages from PDFs in a folder.")
    parser.add_argument("input_folder", help="The input folder containing PDF files.")
    parser.add_argument("--output_folder", help="The output folder to save reduced PDF files.")
    parser.add_argument("--firstN", type=int, default=10, help="Number of first pages to extract.")
    parser.add_argument("--lastN", type=int, default=10, help="Number of last pages to extract.")
    
    args = parser.parse_args()
    
    process_pdfs_in_folder(args.input_folder, args.output_folder, args.firstN, args.lastN)

    # Example usage:
    # python firstAndLastNPages.py "F:\_playground2\_common\testDiscardAfterUse" --output_folder "F:\_playground2\_common\output" --firstN 12 --lastN 12