import os
import shutil
from pdfs import pdfNames

def fileMover(src_dir,dest_dir,file_name):
    # Check if the file already exists in the destination directory
    if os.path.exists(os.path.join(dest_dir, file_name)):
        # If the file exists, append a number to the file name to make it unique
        i = 1
        while os.path.exists(os.path.join(dest_dir, f"{file_name}_{i}")):
            i += 1
        file_name = f"{file_name}_{i}"

    # Move the file to the destination directory
    shutil.move(os.path.join(src_dir, file_name), os.path.join(dest_dir, file_name))

src_dir = 'C:\\tmp\\_data\\test'
dest_dir = 'C:\\tmp\\_data\\tmp'
_pdfNames = pdfNames

def processData(src_dir,dest_dir,pdfNames):
    pdfNamesAsList = pdfNames.split(',')

    for pdf in pdfNamesAsList:
        pdf = pdf.strip()
        fileMover(src_dir,dest_dir,pdf)
        print(pdf)

if __name__ == "__main__":
    processData(src_dir,dest_dir,_pdfNames)
