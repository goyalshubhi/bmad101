from pydantic import BaseModel


class RenderResponse(BaseModel):
    deck_id: str
    version: int
    pptx_url: str
    status: str
