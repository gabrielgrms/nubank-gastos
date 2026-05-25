from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import extract, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import Category, EmailVerificationToken, Expense, NubankLink, User
from app.db.session import get_db
from app.schemas.auth import (
    AnnualDashboardItem,
    AnnualDashboardResponse,
    AverageResponse,
    CategoryResponse,
    CreateCategoryRequest,
    ExpenseResponse,
    FutureDashboardResponse,
    FutureExpenseResponse,
    LoginRequest,
    MessageResponse,
    MonthlyChartItem,
    MonthlyDashboardResponse,
    RegisterRequest,
    TokenResponse,
    UpdateExpenseCategoryRequest,
    UserResponse,
)
from app.services.email_service import send_verification_email

router = APIRouter(prefix="/api")


def _has_nubank_link(db: Session, user_id: int) -> bool:
    return db.scalar(select(NubankLink.id).where(NubankLink.user_id == user_id)) is not None


@router.post("/auth/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já cadastrado")

    user = User(email=payload.email, password_hash=hash_password(payload.password), is_verified=False)
    db.add(user)
    db.flush()

    token = token_urlsafe(32)
    verification = EmailVerificationToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=24),
        used=False,
    )
    db.add(verification)
    db.commit()

    await send_verification_email(payload.email, token)
    return MessageResponse(message="Cadastro realizado. Verifique seu email para confirmar a conta.")


@router.get("/auth/verify", response_model=MessageResponse)
def verify_registration(token: str, db: Session = Depends(get_db)):
    record = db.scalar(select(EmailVerificationToken).where(EmailVerificationToken.token == token))
    if not record or record.used or record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado")

    user = db.scalar(select(User).where(User.id == record.user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    user.is_verified = True
    record.used = True
    db.commit()

    return MessageResponse(message=f"Cadastro confirmado. Faça login em {settings.frontend_base_url}.")


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Confirme seu email antes de acessar")

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        is_verified=current_user.is_verified,
        has_nubank_link=_has_nubank_link(db, current_user.id),
    )


@router.post("/nubank/link", response_model=MessageResponse)
def link_nubank_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    link = db.scalar(select(NubankLink).where(NubankLink.user_id == current_user.id))
    if not link:
        db.add(NubankLink(user_id=current_user.id, provider="nubank"))

    has_expenses = db.scalar(select(Expense.id).where(Expense.user_id == current_user.id)) is not None
    if not has_expenses:
        categories = {c.name: c.id for c in db.scalars(select(Category).where(Category.user_id.is_(None))).all()}
        today = date.today()
        mock_expenses = [
            Expense(
                user_id=current_user.id,
                description="Supermercado",
                amount=Decimal("420.50"),
                due_date=today.replace(day=5),
                category_id=categories.get("Mercado"),
                is_future=False,
            ),
            Expense(
                user_id=current_user.id,
                description="Restaurante",
                amount=Decimal("158.90"),
                due_date=today.replace(day=12),
                category_id=categories.get("Alimentação"),
                is_future=False,
            ),
            Expense(
                user_id=current_user.id,
                description="Streaming anual",
                amount=Decimal("59.90"),
                due_date=today + timedelta(days=40),
                category_id=categories.get("Assinaturas"),
                is_future=True,
                installment_total=4,
                installment_number=2,
            ),
            Expense(
                user_id=current_user.id,
                description="Notebook",
                amount=Decimal("450.00"),
                due_date=today + timedelta(days=70),
                category_id=None,
                is_future=True,
                installment_total=10,
                installment_number=5,
            ),
        ]
        db.add_all(mock_expenses)

    db.commit()
    return MessageResponse(message="Conta Nubank vinculada com sucesso")


@router.get("/dashboard/monthly", response_model=MonthlyDashboardResponse)
def monthly_dashboard(
    month: str | None = Query(default=None, description="Formato YYYY-MM"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _has_nubank_link(db, current_user.id):
        return MonthlyDashboardResponse(linked=False, month=month or date.today().strftime("%Y-%m"), data=[])

    month_date = date.today().replace(day=1)
    if month:
        try:
            month_date = datetime.strptime(month + "-01", "%Y-%m-%d").date()
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mês inválido") from exc

    results = db.execute(
        select(func.coalesce(Category.name, "Sem categoria"), func.sum(Expense.amount))
        .select_from(Expense)
        .join(Category, Category.id == Expense.category_id, isouter=True)
        .where(
            Expense.user_id == current_user.id,
            extract("year", Expense.due_date) == month_date.year,
            extract("month", Expense.due_date) == month_date.month,
            Expense.is_future.is_(False),
        )
        .group_by(Category.name)
    ).all()

    data = [MonthlyChartItem(category=row[0], total=float(row[1] or 0)) for row in results]
    return MonthlyDashboardResponse(linked=True, month=month_date.strftime("%Y-%m"), data=data)


@router.get("/dashboard/annual", response_model=AnnualDashboardResponse)
def annual_dashboard(
    year: int = Query(default=date.today().year),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _has_nubank_link(db, current_user.id):
        return AnnualDashboardResponse(linked=False, year=year, data=[])

    results = db.execute(
        select(extract("month", Expense.due_date), func.sum(Expense.amount))
        .where(
            Expense.user_id == current_user.id,
            extract("year", Expense.due_date) == year,
            Expense.is_future.is_(False),
        )
        .group_by(extract("month", Expense.due_date))
        .order_by(extract("month", Expense.due_date))
    ).all()

    data = [AnnualDashboardItem(month=int(row[0]), total=float(row[1] or 0)) for row in results]
    return AnnualDashboardResponse(linked=True, year=year, data=data)


@router.get("/dashboard/average", response_model=AverageResponse)
def average_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not _has_nubank_link(db, current_user.id):
        return AverageResponse(linked=False, average_last_6_months=None)

    now = date.today().replace(day=1)
    start = (now - timedelta(days=180)).replace(day=1)

    monthly_totals = db.execute(
        select(extract("year", Expense.due_date), extract("month", Expense.due_date), func.sum(Expense.amount))
        .where(
            Expense.user_id == current_user.id,
            Expense.due_date >= start,
            Expense.due_date < now,
            Expense.is_future.is_(False),
        )
        .group_by(extract("year", Expense.due_date), extract("month", Expense.due_date))
    ).all()

    if not monthly_totals:
        return AverageResponse(linked=True, average_last_6_months=0)

    avg = sum(float(row[2]) for row in monthly_totals) / len(monthly_totals)
    return AverageResponse(linked=True, average_last_6_months=round(avg, 2))


@router.get("/dashboard/future", response_model=FutureDashboardResponse)
def future_dashboard(
    year: int = Query(default=date.today().year),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _has_nubank_link(db, current_user.id):
        return FutureDashboardResponse(linked=False, data=[])

    results = db.scalars(
        select(Expense)
        .where(
            Expense.user_id == current_user.id,
            Expense.is_future.is_(True),
            extract("year", Expense.due_date) == year,
        )
        .order_by(Expense.due_date)
    ).all()

    data = [
        FutureExpenseResponse(
            id=item.id,
            description=item.description,
            amount=float(item.amount),
            due_date=item.due_date,
            installment_label=(
                f"{item.installment_number}/{item.installment_total}"
                if item.installment_number and item.installment_total
                else None
            ),
        )
        for item in results
    ]

    return FutureDashboardResponse(linked=True, data=data)


@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    categories = db.scalars(
        select(Category)
        .where((Category.user_id == current_user.id) | (Category.user_id.is_(None)))
        .order_by(Category.name)
    ).all()
    return [CategoryResponse(id=category.id, name=category.name) for category in categories]


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CreateCategoryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    category = Category(user_id=current_user.id, name=payload.name.strip())
    db.add(category)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Categoria já existe") from exc

    db.refresh(category)
    return CategoryResponse(id=category.id, name=category.name)


@router.get("/expenses", response_model=list[ExpenseResponse])
def list_expenses(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    expenses = db.scalars(select(Expense).where(Expense.user_id == current_user.id).order_by(Expense.due_date.desc())).all()
    return [
        ExpenseResponse(
            id=expense.id,
            description=expense.description,
            amount=float(expense.amount),
            due_date=expense.due_date,
            category_id=expense.category_id,
            category_name=expense.category.name if expense.category else None,
            is_future=expense.is_future,
            installment_total=expense.installment_total,
            installment_number=expense.installment_number,
        )
        for expense in expenses
    ]


@router.patch("/expenses/{expense_id}/category", response_model=MessageResponse)
def update_expense_category(
    expense_id: int,
    payload: UpdateExpenseCategoryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    expense = db.scalar(select(Expense).where(Expense.id == expense_id, Expense.user_id == current_user.id))
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gasto não encontrado")

    category = db.scalar(
        select(Category).where(
            Category.id == payload.category_id,
            (Category.user_id == current_user.id) | (Category.user_id.is_(None)),
        )
    )
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria não encontrada")

    expense.category_id = category.id
    db.commit()
    return MessageResponse(message="Categoria atualizada com sucesso")
