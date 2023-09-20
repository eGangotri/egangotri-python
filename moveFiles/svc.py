import os
def getPdfCount(directory):
    pdf_count = 0
    # Loop through all the files in the directory
    for filename in os.listdir(directory):
        # Check if the file is a PDF file
        if filename.endswith('.pdf'):
            # If the file is a PDF file, increment the count
            pdf_count += 1
    return pdf_count