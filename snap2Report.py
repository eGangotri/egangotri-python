import os
import pandas as pd
import time

from pypdf import PdfReader

def get_all_files_in_directory(root_dir):
    """Recursively get all files in a directory."""
    files_list = []
    
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            files_list.append(os.path.join(root, file))
    
    return files_list

def count_pdf_pages(pdf_file):
    reader = PdfReader(pdf_file)
    number_of_pages = len(reader.pages)
    return number_of_pages

def extract_file_details(files_list):
    """Extract details from the list of file paths."""
    data = []
    for file in files_list:
        filename = os.path.basename(file)
        filetype = filename.split('.')[-1] if '.' in filename else 'Unknown'
        
        # If file type is PDF, get the number of pages
        if filetype.lower() == 'pdf':
            try:
                pdf_pages = count_pdf_pages(file)
            except Exception as e:
                print(f"Error reading {file}: {e}")
                pdf_pages = "Error"
        else:
            pdf_pages = "N/A"
        print(filename, filetype, file, pdf_pages)
        data.append((filename, filetype, file, pdf_pages))  # Add page count to the data
    return data

def save_to_excel(data, output_filename):
    """Save data to Excel."""
    df = pd.DataFrame(data, columns=["File Name", "File Type", "Full Path", "PDF Pages"])
    df.index += 1  # so index starts from 1 instead of 0
    df.to_excel(output_filename, index_label="Index", engine='openpyxl')

if __name__ == "__main__":
    directory_to_scan = "E:\\"  # Replace with your directory path
    output_filename = "output.xlsx"  # Replace with desired output name

    # Start the timer
    start_time = time.time()

    files = get_all_files_in_directory(directory_to_scan)
    details = extract_file_details(files)
    save_to_excel(details, output_filename)

    # Calculate and print the time consumed
    end_time = time.time()
    time_consumed = end_time - start_time
    print(f"Time consumed: {time_consumed:.2f} seconds")
