from pydantic import BaseModel, Field
from datetime import datetime


class Author(BaseModel):
    id: int
    create_time: datetime = Field(default_factory=datetime.utcnow)
    name: str
    platform: str


class Platform(BaseModel):
    ...
