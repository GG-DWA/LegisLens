from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import views
from app.routers.laws import router as laws_router

import json


app = FastAPI(title="LegisLens API")

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)

app.include_router(laws_router)
app.include_router(views.router)


@app.get("/")
def home():
    return {"message": "LegisLens API is running"}


@app.get("/api/law-profile")
def get_law_profile():
    with open(
        "data/law_profile_analyzed.json",
        "r",
        encoding="utf-8",
    ) as f:
        data = json.load(f)

    return data