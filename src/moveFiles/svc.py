import os
def getPdfCount(directory):
    return getFileTypeCount(directory, ".pdf")

def getCr2Count(directory):
    return getFileTypeCount(directory, ".cr2")

def getJpgCount(directory):
    return getFileTypeCount(directory, [".jpg", ".jpeg"])

def getPnrCount(directory):
    return getFileTypeCount(directory, ".png")


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