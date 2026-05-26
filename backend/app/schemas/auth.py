from datetime import date
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_verified: bool
    has_nubank_link: bool


class CategoryResponse(BaseModel):
    id: int
    name: str


class CreateCategoryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ExpenseResponse(BaseModel):
    id: int
    description: str
    amount: float
    due_date: date
    category_id: int | None
    category_name: str | None
    is_future: bool
    installment_total: int | None
    installment_number: int | None


class UpdateExpenseCategoryRequest(BaseModel):
    category_id: int | None


class MonthlyChartItem(BaseModel):
    category: str
    total: float


class MonthlyDashboardResponse(BaseModel):
    linked: bool
    month: str
    data: list[MonthlyChartItem]


class AnnualDashboardItem(BaseModel):
    month: int
    total: float


class AnnualDashboardResponse(BaseModel):
    linked: bool
    year: int
    data: list[AnnualDashboardItem]


class AverageResponse(BaseModel):
    linked: bool
    average_last_6_months: float | None


class FutureExpenseResponse(BaseModel):
    id: int
    description: str
    amount: float
    due_date: date
    installment_label: str | None


class FutureDashboardResponse(BaseModel):
    linked: bool
    data: list[FutureExpenseResponse]
