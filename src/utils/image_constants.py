from enum import Enum
from typing import Set

class ImageType(str, Enum):
    ANY = "ANY"
    JPG = "JPG"
    PNG = "PNG"
    TIF = "TIF"
    CR2 = "CR2"

def get_extensions_for_type(img_type: ImageType) -> Set[str]:
    if img_type == ImageType.ANY:
        return {'.jpg', '.jpeg', '.png', '.cr2', '.tiff', '.tif'}
    elif img_type == ImageType.JPG:
        return {'.jpg', '.jpeg'}
    elif img_type == ImageType.PNG:
        return {'.png'}
    elif img_type == ImageType.TIF:
        return {'.tiff', '.tif'}
    elif img_type == ImageType.CR2:
        return {'.cr2'}
    return set()
