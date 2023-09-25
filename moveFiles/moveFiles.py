import os
import shutil
from pdfs import pdfNames
from svc import getPdfCount


def fileMover(src_dir, dest_dir, file_name):
    # Check if the file already exists in the destination directory
    if os.path.exists(os.path.join(dest_dir, file_name)):
        # If the file exists, append a number to the file name to make it unique
        i = 1
        while os.path.exists(os.path.join(dest_dir, f"{file_name}_{i}")):
            i += 1
        file_name = f"{file_name}_{i}"

    # Move the file to the destination directory
    shutil.move(os.path.join(src_dir, file_name),
                os.path.join(dest_dir, file_name))


src_dir = 'C:\\tmp\\_freeze\\test'
dest_dir = 'C:\\tmp\\_data\\test'

def processData(src_dir, dest_dir, pdfNames=""):
    pdfNamesAsList = []
    if (pdfNames == ""):
        # get list of all files in src_dir
        for file in os.listdir(src_dir):
            pdfNamesAsList.append(file) # add file to list

    else:
        pdfNamesAsList = pdfNames.split(',')
    print(f"Shall move {pdfNamesAsList}")
    print(f"Shall move {len(pdfNamesAsList)}")
    print(f"src_dir pdf count before {getPdfCount(src_dir)}")
    print(f"dest_dir pdf count before {getPdfCount(dest_dir)}")

    for pdf in pdfNamesAsList:
        pdf = pdf.strip()
        fileMover(src_dir, dest_dir, pdf)
        print(pdf)
    # how find count of pdfs in folfer stored in dest_dir

    print(f"Shall move {len(pdfNamesAsList)}")
    print(f"src_dir pdf count after {getPdfCount(src_dir)}")
    print(f"dest_dir pdf count after {getPdfCount(dest_dir)}")


if __name__ == "__main__":
    processData(src_dir, dest_dir, "")

# python moveFiles/moveFiles.py
