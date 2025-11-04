from fastapi import UploadFile, Depends, File, HTTPException
from fastapi.routing import APIRouter

from app.controller.controller import PipelineController
from app.models.upload_response import FileResponse

def get_pipeline() -> PipelineController:
    return PipelineController()

router = APIRouter()

@router.post("/upload", response_model=FileResponse)
def upload_file(
        file: UploadFile = File(...),
        pipeline: PipelineController = Depends(get_pipeline)
):
    print("PROCESSING REQUEST")
    try:
        print("TESTING FILE EXTENSION")

        print("CALLED CONTROLLER")
        result = pipeline.file_handler(file)

        response = {
            "status" : "success",
            **result
        }

        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

