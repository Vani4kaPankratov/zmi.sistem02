from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend import models, database
from pathlib import Path

# =====================================================
# Створюємо всі таблиці
# =====================================================
database.Base.metadata.create_all(bind=database.engine)

# =====================================================
# Ініціалізація FastAPI
# =====================================================
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="supersecret")

# Шаблони для сайту
from pathlib import Path
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "frontend" / "templates")
)


# =====================================================
# Pydantic моделі
# =====================================================
class RegisterRequest(BaseModel):
    nickname: str
    phone: str
    email: str
    password: str

class LoginRequest(BaseModel):
    nickname: str
    password: str
    telegram_id: str | None = None

# =====================================================
# Головна сторінка
# =====================================================
@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/login")

# =====================================================
# Сторінка логіну
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
    db: Session = next(database.get_db())
    nickname = f"{first_name} {last_name}"
    user = db.query(models.User).filter(models.User.nickname == nickname).first()

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
# Реєстрація користувача через бот
# =====================================================
@app.post("/register")
def register_user(data: RegisterRequest):
    db: Session = next(database.get_db())

    if db.query(models.User).filter(models.User.nickname == data.nickname).first():
        raise HTTPException(status_code=400, detail="Такий нікнейм уже існує")

    new_user = models.User(
        nickname=data.nickname,
        phone=data.phone,
        email=data.email,
        password=data.password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "Користувач зареєстрований"}

# =====================================================
# Вхід користувача через бот
# =====================================================
@app.post("/login_bot")
def login_user(data: LoginRequest):
    db: Session = next(database.get_db())
    user = db.query(models.User).filter(models.User.nickname == data.nickname).first()

    if not user or user.password != data.password:
        raise HTTPException(status_code=401, detail="Невірний нікнейм або пароль")

    if data.telegram_id:
        user.telegram_id = data.telegram_id
        db.commit()

    return {"nickname": user.nickname}

# =====================================================
# Отримати користувача по Telegram ID
# =====================================================
@app.get("/user_by_telegram/{telegram_id}")
def get_user_by_telegram(telegram_id: str):
    db: Session = next(database.get_db())
    user = db.query(models.User).filter(models.User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Користувача не знайдено")
    return {"nickname": user.nickname}
