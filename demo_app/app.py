# Importing required libraries and modules

import json
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


app = FastAPI(title="Northwind Community Bank")

# Creating Base folder for templates, static files, and demo data

app_folder = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=str(app_folder / "templates"))

app.mount(
    "/static",
    StaticFiles(directory=str(app_folder / "static")),
    name="static"
)


# Loading the synthetic member data once when the app starts

def load_members():
    data_file = app_folder / "data" / "members.json"

    with open(data_file, "r", encoding="utf-8") as file:
        return json.load(file)


members = load_members()


# Show the member search page

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="search.html",
        context={}
    )


# Search for a member using the entered member number

@app.post("/member-search", response_class=HTMLResponse)
async def member_search(
    request: Request,
    member_id: str = Form(...)
):
    member_id = member_id.strip()
    member = members.get(member_id)

    if member is None:
        return templates.TemplateResponse(
            request=request,
            name="not_found.html",
            context={"member_id": member_id}
        )

    return templates.TemplateResponse(
        request=request,
        name="member.html",
        context={"member": member}
    )