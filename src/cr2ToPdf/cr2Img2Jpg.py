import os
import rawpy
import fitz  # PyMuPDF
from PIL import Image
import time
from src.moveFiles.svc import getCr2Count
from src.utils.utils import format_time_taken


def convert_cr2_to_image(cr2_path, output_image_path):
    """Convert a .CR2 file to a JPEG image."""
    with rawpy.imread(cr2_path) as raw:
        rgb = raw.postprocess()
    image = Image.fromarray(rgb)
    image.save(output_image_path, "JPEG")

def convert_cr2_folder_to_jpg(cr2_folder, output_jpg_path):
    """Convert all .CR2 files in a folder and its subfolders to JPEG images, maintaining the directory structure."""
    start_time = time.time()
    print(f"convert_cr2_folder_to_jpg: Start time: {format_time_taken(start_time)}")

    print(f"convert_cr2_folder_to_jpg: {cr2_folder} to {output_jpg_path}")
    os.makedirs(output_jpg_path, exist_ok=True)
    msgs = []
    converted_count = 0  # Initialize counter

    # Walk through the directory tree
    for root, dirs, files in os.walk(cr2_folder):
        for cr2_file in files:
            if cr2_file.lower().endswith('.cr2'):
                cr2_path = os.path.join(root, cr2_file)
                relative_path = os.path.relpath(root, cr2_folder)
                output_dir = os.path.join(output_jpg_path, relative_path)
                os.makedirs(output_dir, exist_ok=True)
                image_path = os.path.join(output_dir, f"{os.path.splitext(cr2_file)[0]}.jpg")
                convert_cr2_to_image(cr2_path, image_path)
                converted_count += 1
                print(f"Converted Cr2 from {cr2_file} to {image_path}")

    msgs.append(f"Converted {converted_count} Cr2 files")

    end_time = time.time()
    time_taken = end_time - start_time

    # Format time taken using the utility function
    time_taken_str = format_time_taken(time_taken)
    print(f"time_taken_str {time_taken_str}")

    # Return the result as a JSON object
    result = {
        "output_jpg_path": output_jpg_path,
        "output": f"{converted_count} files converted",
        "success": True,
        "msgs": msgs,
        "time_taken": time_taken_str
    }

    print(f"result {result}")

    return result