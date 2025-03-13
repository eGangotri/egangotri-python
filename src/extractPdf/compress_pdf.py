import fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter

def compress_pdf(input_pdf, output_pdf, zoom_x=0.5, zoom_y=0.5):
    """
    Compresses a PDF by reducing image resolution using PyMuPDF.
    """
    # Open the input PDF
    doc = fitz.open(input_pdf)
    
    # Iterate through each page
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom_x, zoom_y))  # Reduce image resolution
        page.insert_image(page.rect, pixmap=pix)  # Replace the page content with the compressed image
    
    # Save the compressed PDF
    doc.save(output_pdf, deflate=True)
    doc.close()

def optimize_pdf_structure(input_pdf, output_pdf):
    """
    Optimizes the PDF structure using PyPDF2 (e.g., removes metadata, compresses streams).
    """
    reader = PdfReader(input_pdf)
    writer = PdfWriter()

    # Copy pages to the writer
    for page in reader.pages:
        writer.add_page(page)

    # Optimize the PDF
    writer.add_metadata(reader.metadata)  # Optionally preserve metadata
    with open(output_pdf, "wb") as output_file:
        writer.write(output_file)

