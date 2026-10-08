from pydantic import BaseModel, Field


class ForgotPasswordRequest(BaseModel):
    """
    Accepts either employee ID or email.
    """

    identifier: str = Field(
        ...,
        examples=["EMP001"],
        description="Employee ID or Email",
    )


class VerifyResetTokenRequest(BaseModel):
    token: str


class ResetPasswordRequest(BaseModel):
    token: str

    new_password: str = Field(
        min_length=8,
        max_length=128,
        examples=["NewPassword@123"],
    )


class ForgotPasswordResponse(BaseModel):
    message: str
    student: bool
    token: str | None = None


class VerifyResetTokenResponse(BaseModel):
    valid: bool
    message: str


class ResetPasswordResponse(BaseModel):
    message: str
