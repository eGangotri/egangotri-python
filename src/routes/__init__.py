from fastapi import APIRouter

router = APIRouter()

# Import routers from packages
from src.routes.img_to_pdf import img_folder_router, verify_router, pdf_merge_router

# Include sub-routers
router.include_router(img_folder_router, prefix="/img-to-pdf", tags=["Image to PDF"])
router.include_router(verify_router, prefix="/verify", tags=["PDF Verification"])
router.include_router(pdf_merge_router, prefix="/pdf", tags=["PDF Merge"])