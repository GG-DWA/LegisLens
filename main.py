from fastapi import FastAPI
import json

app = FastAPI(title="LegisLens API")

@app.get("/")
def home():
    return {"message": "LegisLens API is running"}

@app.get("/api/law-profile")
def get_law_profile():
    with open("law_profile_analyzed.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return data