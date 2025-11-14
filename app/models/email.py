from pydantic import BaseModel

class EmailSchema(BaseModel):
    from_: str
    to_: str
    subject: str
    body: str
