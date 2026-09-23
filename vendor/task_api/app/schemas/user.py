from pydantic import BaseModel, EmailStr, Field, field_validator

class RegisterUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)

    @field_validator('username')
    @classmethod
    def validate_username(cls, username: str) -> str:
        if (username is None or
            username.strip() == "" or
            len(username.strip()) < 3):
            raise ValueError(
                'Username cannot be blank or less than 3 characters'
            )
        return username

class LoginUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)