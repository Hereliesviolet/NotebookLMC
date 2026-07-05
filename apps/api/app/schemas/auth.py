from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: str

    class Config:
        from_attributes = True
