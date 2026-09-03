import os
import sys

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

import library

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKING_DIR = os.path.dirname(CURRENT_DIR)
sys.path.append(WORKING_DIR)

from api_routes import PREVIEW_DIR, router

VIRALS_DIR = os.path.join(WORKING_DIR, "VIRALS")
STATIC_DIR = os.path.join(CURRENT_DIR, "static")
INDEX_PATH = os.path.join(STATIC_DIR, "index.html")

os.makedirs(VIRALS_DIR, exist_ok=True)
os.makedirs(os.path.join(WORKING_DIR, "models"), exist_ok=True)
os.makedirs(PREVIEW_DIR, exist_ok=True)

library.set_url_mode("fastapi")

app = FastAPI(title="ViralCutter")
app.include_router(router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/virals", StaticFiles(directory=VIRALS_DIR), name="virals")
app.mount("/preview", StaticFiles(directory=PREVIEW_DIR), name="preview")


@app.get("/")
def index():
    return FileResponse(INDEX_PATH)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
