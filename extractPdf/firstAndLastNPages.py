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

def process_pdfs_in_folder(input_folder, firstN=10, lastN=10):
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
        relative_path = os.path.relpath(root, input_folder)
        output_folder = os.path.join(input_folder, REDUCED_FOLDER, relative_path)
        os.makedirs(output_folder, exist_ok=True)
        output_pdf = os.path.join(output_folder, file)
        extract_first_and_last_n_pages(input_pdf, output_pdf, firstN, lastN)
        print(f"{count}/{total_files}) {file} reduced to {firstN + lastN} pages")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract first and last N pages from PDFs in a folder.")
    parser.add_argument("input_folder", help="The input folder containing PDF files.")
    parser.add_argument("--firstN", type=int, default=10, help="Number of first pages to extract.")
    parser.add_argument("--lastN", type=int, default=10, help="Number of last pages to extract.")
    
    args = parser.parse_args()
    
    process_pdfs_in_folder(args.input_folder, args.firstN, args.lastN)

    # python firstAndLastNPages.py "F:\_playground2\_common\testDiscardAfterUse" --firstN 12 --lastN 12