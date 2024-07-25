from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel
from contextlib import asynccontextmanager
from database import Db
from user_service import UserService
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from config import SECRET_KEY
import jwt
from datetime import datetime, timezone
from fastapi.security import OAuth2PasswordBearer
from product_service import ProductService
from typing import Optional


class User(BaseModel):
    username: str
    password: str


class Product(BaseModel):
    product_name: str
    price: float
    unique_code: str
    product_info: str


class UpdateProduct(BaseModel):
    product_name: Optional[str] = None
    price: Optional[float] = None
    product_info: Optional[str] = None
    unique_code: Optional[str] = None


db = Db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    yield
    await db.close()

app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost",
    'http://localhost:5173',
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_user_service():
    return UserService(db)


def get_product_service():
    return ProductService(db)


@app.post("/register")
async def register(user: User, user_service: UserService = Depends(get_user_service)):
    response, status = await user_service.create_user(user.username, user.password)
    return JSONResponse(content=response, status_code=status)


@app.post("/login")
async def login(user: User, user_service: UserService = Depends(get_user_service)):
    response, status = await user_service.login_user(user.username, user.password)
    if status != 200:
        raise HTTPException(status_code=status, detail=response['message'])
    return JSONResponse(content=response, status_code=status)


@app.post('/verify-token')
async def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        exp = datetime.fromtimestamp(payload.get("exp"), timezone.utc)
        if exp < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Token expired")
        return {"valid": True}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/products")
async def get_products(page: int = Query(1, ge=1), page_size: int = Query(10, le=100), sort_by: str = Query('update_time', regex="^[a-zA-Z_]+$"), order_by: str = Query('desc', regex="^(asc|desc)$"), search_query: Optional[str] = Query(None), product_service: ProductService = Depends(get_product_service)):
    try:
        products_data = await product_service.get_products(page, page_size, sort_by, order_by, search_query)
        return products_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/product")
async def create_product(product: Product, product_service: ProductService = Depends(get_product_service)):
    return await product_service.create_product(product)


@app.put("/product/{product_id}")
async def update_product(product_id: str, product: UpdateProduct, product_service: ProductService = Depends(get_product_service)):
    return await product_service.update_product(product_id, product)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
