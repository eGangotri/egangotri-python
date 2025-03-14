from fastapi import APIRouter

router = APIRouter()

# Import your controllers here and define your routes
# Example:
# from src.controllers.example_controller import ExampleController
# router.add_api_route("/example", ExampleController.some_method, methods=["GET"])

from src.routes.pdf_merge import router as pdf_merge_router
router.include_router(pdf_merge_router)