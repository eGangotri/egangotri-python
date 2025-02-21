import os
import shutil
import json
import time
from src.utils.utils import format_time_taken

def copy_all_pdfs(input_folder, output_folder=None):
    if output_folder is None:
        output_folder = input_folder + "-copy"
    
    # Calculate total files expected
    total_files_expected = sum(
        len([file for file in files if file.lower().endswith('.pdf')])
        for _, _, files in os.walk(input_folder)
    )
    
    files_copied = []
    msgs = []
    start_time = time.time()
    
    for root, dirs, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith('.pdf'):
                # Construct full file path
                file_path = os.path.join(root, file)
                # Construct the corresponding output directory
                relative_path = os.path.relpath(root, input_folder)
                output_dir = os.path.join(output_folder, relative_path)
                # Create the output directory if it doesn't exist
                os.makedirs(output_dir, exist_ok=True)
                # Copy the file to the output directory
                shutil.copy(file_path, output_dir)
                # Add the file to the list of copied files
                files_copied.append(file_path)
                # Print the name of the file just copied
                print(f"({len(files_copied)}/{total_files_expected}). Copied: {file_path}")
                # Add the message with numbering
                msgs.append(f"({len(files_copied)}/{total_files_expected}). Copied: {file_path}")
    
    end_time = time.time()
    time_taken = end_time - start_time
    
    # Format time taken using the utility function
    time_taken_str = format_time_taken(time_taken)
    
    # Return the result as a JSON object
    result = {
        "success": len(files_copied) == total_files_expected,
        "time_taken": time_taken_str,
        "status": f"Copied {len(files_copied)}/{total_files_expected} pdfs from {input_folder} to {output_folder}",
        "output_folder": output_folder,
        "files_copied_count": len(files_copied),
        "total_files_expected": total_files_expected,
        "counts_match": len(files_copied) == total_files_expected,
        "msgs": msgs,
    }
    return result

# Example usage
# result = copy_all_pdfs('path/to/input_folder', 'path/to/output_folder')
# print(json.dumps(result, indent=4))