from datetime import datetime
from pydantic import BaseModel

class FileResponse(BaseModel):
    status: str
    file_name: str
    timestamp: datetime