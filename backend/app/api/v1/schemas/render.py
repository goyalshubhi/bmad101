from pydantic import BaseModel


class RenderResponse(BaseModel):
    deck_id: str
    version: int
    download_url: str
    status: str


class RenderStatusResponse(BaseModel):
    status: str
    download_url: str | None = None
