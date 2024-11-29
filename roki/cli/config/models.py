from pydantic import BaseModel, field_validator


class Key(BaseModel):
    name: str
    value: str
    description: str
    icon: str

    def __hash__(self) -> int:
        return self.name.__hash__()

    @field_validator("description")
    def validade_description(cls, desc: str):
        return desc.replace("``", "")
