from fastapi import FastAPI
from starlette.middleware import Middleware

from app.api.routers.chat_router import chat_router
from app.core.lifespan import lifespan
from app.core.middleware import RequestIDMiddleware

# 用 Middleware(...) 包装传入, 避免新版 Starlette 对 add_middleware 的严格类型检查报错
app = FastAPI(lifespan=lifespan, middleware=[Middleware(RequestIDMiddleware)])

app.include_router(chat_router)
