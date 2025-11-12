from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    nickname: str
    phone: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    nickname: str
    password: str

class UserResponse(BaseModel):
    id: int
    nickname: str
    email: str
    role: str

    class Config:
        from_attributes = True  # ✅ новий синтаксис для Pydantic v2