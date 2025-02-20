import os
# Constants for file type suffixes
FILETYPE_PDF = ".pdf"
FILETYPE_CR2 = ".cr2"
FILETYPE_JPG = [".jpg", ".jpeg"]
FILETYPE_PNG = ".png"

def getPdfCount(directory, includeSubFolders=False):
    if includeSubFolders:
        return getFileTypeCountIncludeSubFolders(directory, FILETYPE_PDF)
    return getFileTypeCount(directory, FILETYPE_PDF)

def getCr2Count(directory, includeSubFolders=False):
    if includeSubFolders:
        return getFileTypeCountIncludeSubFolders(directory, FILETYPE_CR2)
    return getFileTypeCount(directory, FILETYPE_CR2)

def getJpgCount(directory, includeSubFolders=False):
    if includeSubFolders:
        return getFileTypeCountIncludeSubFolders(directory, FILETYPE_JPG)
    return getFileTypeCount(directory, FILETYPE_JPG)

def getPnrCount(directory, includeSubFolders=False):
    if includeSubFolders:
        return getFileTypeCountIncludeSubFolders(directory, FILETYPE_PNG)
    return getFileTypeCount(directory, FILETYPE_PNG)

def getFileTypeCount(directory, suffix):
    file_count = 0
    # Ensure suffix is a list for uniform processing
    if isinstance(suffix, str):
        suffix = [suffix]
    
    # Loop through all the files in the directory
    for filename in os.listdir(directory):
        # Check if the file ends with any of the suffixes
        if any(filename.lower().endswith(s) for s in suffix):
            # If the file matches any suffix, increment the count
            file_count += 1
    return file_count

def getFileTypeCountIncludeSubFolders(directory, suffix):
    file_count = 0
    # Ensure suffix is a list for uniform processing
    if isinstance(suffix, str):
        suffix = [suffix]
    
    # Walk through all the files and subdirectories in the directory
    for root, _, files in os.walk(directory):
        for filename in files:
            # Check if the file ends with any of the suffixes
            if any(filename.lower().endswith(s) for s in suffix):
                # If the file matches any suffix, increment the count
                file_count += 1
    return file_count