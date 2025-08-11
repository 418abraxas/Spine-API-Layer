from fastapi import FastAPI
from .routes import api
from .config import settings

app = FastAPI(title=settings.APP_NAME)
app.include_router(api)

@app.get("/")
def root():
    return {"ok": True, "name": settings.APP_NAME}
