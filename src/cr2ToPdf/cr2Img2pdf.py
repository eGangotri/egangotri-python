import os
import rawpy
import fitz  # PyMuPDF
from PIL import Image
import time
from src.utils.utils import format_time_taken


def convert_cr2_to_image(cr2_path, output_image_path):
    """Convert a .CR2 file to a JPEG image."""
    with rawpy.imread(cr2_path) as raw:
        rgb = raw.postprocess()
    image = Image.fromarray(rgb)
    image.save(output_image_path, "JPEG")


def convert_images_to_pdf(image_folder, output_pdf_path):
    """Convert all images in a folder to a single PDF."""
    try:
        doc = fitz.open()
        for image_name in sorted(os.listdir(image_folder)):
            if image_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                image_path = os.path.join(image_folder, image_name)
                print(f"Processing image: {image_path}")  # Debugging statement
                if not os.path.exists(image_path):
                    print(f"Image file does not exist: {image_path}")
                    continue
                try:
                    img = Image.open(image_path)
                except Exception as e:
                    print(f"Failed to open image {image_path}: {e}")
                    continue
                try:
                    img_rgb = img.convert("RGB")
                    img_bytes = img_rgb.tobytes("raw", "RGB")
                    width, height = img.size
                    pix = fitz.Pixmap(fitz.csRGB, width, height, img_bytes)
                    pdf_page = fitz.open()
                    pdf_page.insert_page(-1, width=width, height=height)
                    pdf_page[0].insert_image(fitz.Rect(0, 0, width, height), pixmap=pix)
                    doc.insert_pdf(pdf_page)
                except Exception as e:
                    print(f"Failed to convert image to PDF page: {e}")
                    continue
        doc.save(output_pdf_path)
        doc.close()
    except Exception as e:
        print(f"Failed to convert images to PDF: {e}")
        return False
    return True

def convert_cr2_folder_to_pdf(cr2_folder, output_pdf_path):
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
    for cr2_file in os.listdir(cr2_folder):
        if cr2_file.lower().endswith('.cr2'):
            cr2_path = os.path.join(cr2_folder, cr2_file)
            image_path = os.path.join(
                temp_image_folder, f"{os.path.splitext(cr2_file)[0]}.jpg")
            convert_cr2_to_image(cr2_path, image_path)
            converted_count += 1
            print(
                f"({converted_count}). Converted Cr2 from {cr2_file} to {image_path}")

    msgs.append(f"Converted {converted_count} Cr2s")

    # Convert all JPEG images to a single PDF
    # conversionRes = convert_images_to_pdf(temp_image_folder, output_pdf_path)
    # if(not conversionRes):
    #     msgs.append(f"Failed to convert images to PDF")
    #     return {
    #         "output_pdf_path": None,
    #         "total_files_expected": converted_count,
    #         "msgs": msgs,
    #         "time_taken": format_time_taken( time.time() - start_time)
    #     }
    msgs.append(f"Converted Pdf from {temp_image_folder} to {output_pdf_path}")
    print(f"Converted Pdf from {temp_image_folder} to {output_pdf_path}")

    # Clean up temporary image folder
    # for image_file in os.listdir(temp_image_folder):
    #     os.remove(os.path.join(temp_image_folder, image_file))

    # os.rmdir(temp_image_folder)
    end_time = time.time()
    time_taken = end_time - start_time

    # Format time taken using the utility function
    time_taken_str = format_time_taken(time_taken)
    print(f"time_taken_str {time_taken_str}")

    # Return the result as a JSON object
    result = {
        "output_pdf_path": output_pdf_path,
        "total_files_expected": converted_count,
        "msgs": msgs,
        "time_taken": time_taken_str
    }

    print(f"result {result}")

    return result

# if __name__ == "__main__":
#     cr2_folder = "path/to/your/cr2/folder"  # Replace with your folder path
#     output_pdf_path = "output.pdf"  # Replace with your desired output PDF path
#     convert_cr2_folder_to_pdf(cr2_folder, output_pdf_path)
#     print(f"PDF created successfully at {output_pdf_path}")
