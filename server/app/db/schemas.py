from datetime import datetime

from pydantic import BaseModel


class TemplateBase(BaseModel):
    name: str


class TemplateCreate(TemplateBase):
    pass


class TemplateUpdate(TemplateBase):
    pass


class TemplatePublic(TemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
