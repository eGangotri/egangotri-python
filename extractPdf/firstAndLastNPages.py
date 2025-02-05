import fitz  # PyMuPDF

def extract_first_25_pages(input_pdf, output_pdf):
    doc = fitz.open(input_pdf)
    new_doc = fitz.open()
    for i in range(min(25, len(doc))):
        new_doc.insert_pdf(doc, from_page=i, to_page=i)
    new_doc.save(output_pdf)
    new_doc.close()

extract_first_25_pages('C:\\Users\\chetan\\Downloads\\test\\test1.pdf',
                        'C:\\Users\\chetan\\Downloads\\test2\\2.pdf')