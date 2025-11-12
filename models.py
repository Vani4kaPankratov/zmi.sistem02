from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend import database, models

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="supersecret")

templates = Jinja2Templates(directory="../frontend/templates")

# =====================================================
# 🔹 Pydantic моделі (для запитів із бота)
# =====================================================

class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    password: str
    telegram_id: str | None = None


class LoginRequest(BaseModel):
    first_name: str
    last_name: str
    password: str
    telegram_id: str | None = None


# =====================================================
# 🔹 Головна сторінка сайту
# =====================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/login")


# =====================================================
# 🔹 Сторінка логіну на сайті
# =====================================================

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "message": ""})


@app.post("/login", response_class=HTMLResponse)
async def login_post(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    password: str = Form(...)
):
    db = next(database.get_db())

    user = (
        db.query(models.User)
        .filter(models.User.first_name == first_name, models.User.last_name == last_name)
        .first()
    )

    if not user:
        message = "❌ Користувача не знайдено. Зареєструйтеся в боті."
    elif user.password != password:
        message = "❌ Неправильний пароль."
    else:
        request.session["user"] = user.id
        return templates.TemplateResponse(
            "dashboard.html",
            {"request": request, "user": user}
        )

    return templates.TemplateResponse("login.html", {"request": request, "message": message})


# =====================================================
# 🔹 Реєстрація користувача (через бот)
# =====================================================

@app.post("/register")
def register_user(data: RegisterRequest):
    db: Session = next(database.get_db())

    existing_user = (
        db.query(models.User)
        .filter(models.User.first_name == data.first_name, models.User.last_name == data.last_name)
        .first()
    )
    if existing_user:
        raise HTTPException(status_code=400, detail="Такий користувач уже існує")

    new_user = models.User(
        first_name=data.first_name,
        last_name=data.last_name,
        password=data.password,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "✅ Користувача зареєстровано успішно"}


# =====================================================
# 🔹 Вхід користувача через бот
# =====================================================

@app.post("/bot_login")
def login_user(data: LoginRequest):
    db: Session = next(database.get_db())

    user = (
        db.query(models.User)
        .filter(models.User.first_name == data.first_name, models.User.last_name == data.last_name)
        .first()
    )

    if not user or user.password != data.password:
        raise HTTPException(status_code=401, detail="Невірне ім’я або пароль")

    # Якщо бот передає telegram_id — оновлюємо
    if data.telegram_id:
        setattr(user, "telegram_id", data.telegram_id)
        db.commit()

    return {"first_name": user.first_name, "last_name": user.last_name}


# =====================================================
# 🔹 Отримати користувача по telegram_id
# =====================================================

@app.get("/user_by_telegram/{telegram_id}")
def get_user_by_telegram(telegram_id: str):
    db = next(database.get_db())

    if not hasattr(models.User, "telegram_id"):
        raise HTTPException(status_code=400, detail="Модель User не має поля telegram_id")

    user = db.query(models.User).filter(models.User.telegram_id == telegram_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="Користувача не знайдено")

    return {"first_name": user.first_name, "last_name": user.last_name}
