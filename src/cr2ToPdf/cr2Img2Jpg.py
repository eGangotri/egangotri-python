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



def convert_cr2_folder_to_jpg(cr2_folder, output_pdf_path):
    """Convert all .CR2 files in a folder to a single PDF."""
    start_time = time.time()
    print(
        f"convert_cr2_folder_to_pdf:Start time: {format_time_taken(start_time)}")

    print(f"convert_cr2_folder_to_pdf: {cr2_folder} to {output_pdf_path}")
    temp_image_folder = os.path.join(output_pdf_path, "temp_images")
    os.makedirs(temp_image_folder, exist_ok=True)
    msgs = []
    converted_count = 0  # Initialize counter

    # Convert all .CR2 files to JPEG images
    cr2_count = getCr2Count(cr2_folder)
    for cr2_file in os.listdir(cr2_folder):
        if cr2_file.lower().endswith('.cr2'):
            cr2_path = os.path.join(cr2_folder, cr2_file)
            image_path = os.path.join(
                temp_image_folder, f"{os.path.splitext(cr2_file)[0]}.jpg")
            convert_cr2_to_image(cr2_path, image_path)
            converted_count += 1
            print(
                f"({converted_count}/{cr2_count}). Converted Cr2 from {cr2_file} to {image_path}")

    msgs.append(f"Converted {converted_count} of {cr2_count} Cr2s")

    end_time = time.time()
    time_taken = end_time - start_time

    # Format time taken using the utility function
    time_taken_str = format_time_taken(time_taken)
    print(f"time_taken_str {time_taken_str}")

    # Return the result as a JSON object
    result = {
        "output_pdf_path": output_pdf_path,
        "output": f"{converted_count}/{cr2_count} converted",
        "success": cr2_count == converted_count,
        "msgs": msgs,
        "time_taken": time_taken_str
    }

    print(f"result {result}")

    return result
