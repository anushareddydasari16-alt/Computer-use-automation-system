# Runs the Northwind Community Bank demo application.

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


app = FastAPI(title="Northwind Community Bank")

# Base folder for templates, static files, and demo data
app_folder = Path(__file__).resolve().parent

templates = Jinja2Templates(
    directory=str(app_folder / "templates")
)

app.mount(
    "/static",
    StaticFiles(directory=str(app_folder / "static")),
    name="static"
)


# Load synthetic member data when the application starts
def load_members():
    data_file = app_folder / "data" / "members.json"

    with open(data_file, "r", encoding="utf-8") as file:
        return json.load(file)


members = load_members()


# Show the member search page and controlled test conditions
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):

    if request.query_params.get("permission") == "denied":
        return templates.TemplateResponse(
            request=request,
            name="permission_denied.html",
            context={}
        )

    if request.query_params.get("slow") == "1":
        await asyncio.sleep(4)

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

    # Reserved test number used to simulate permission failure
    if member_id == "70007":
        return templates.TemplateResponse(
            request=request,
            name="permission_denied.html",
            context={}
        )

    # Reserved test member used to simulate a temporary processing screen
    if member_id == "80008":
        return templates.TemplateResponse(
            request=request,
            name="processing.html",
            context={
                "member_id": member_id
            }
        )

    member = members.get(member_id)

    if member is None:
        return templates.TemplateResponse(
            request=request,
            name="not_found.html",
            context={
                "member_id": member_id
            }
        )

    return templates.TemplateResponse(
        request=request,
        name="member.html",
        context={
            "member": member
        }
    )


# Continue after the temporary processing screen
@app.post("/member-search/continue", response_class=HTMLResponse)
async def continue_member_search(
    request: Request,
    member_id: str = Form(...)
):
    member_id = member_id.strip()

    member = members.get(member_id)

    if member is None:
        return templates.TemplateResponse(
            request=request,
            name="not_found.html",
            context={
                "member_id": member_id
            }
        )

    return templates.TemplateResponse(
        request=request,
        name="member.html",
        context={
            "member": member
        }
    )


# Open the new account form
@app.get("/new-account", response_class=HTMLResponse)
async def new_account(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="new_account.html",
        context={}
    )


# Validate member and account type before review
@app.post("/new-account/review", response_class=HTMLResponse)
async def review_new_account(
    request: Request,
    member_id: str = Form(...),
    account_type: str = Form(...),
    opening_deposit: float = Form(...)
):
    member_id = member_id.strip()

    member = members.get(member_id)

    if member is None:
        return templates.TemplateResponse(
            request=request,
            name="not_found.html",
            context={
                "member_id": member_id
            }
        )

    existing_accounts = member.get(
        "accounts",
        []
    )

    for account in existing_accounts:
        if account["type"].lower() == account_type.lower():
            return templates.TemplateResponse(
                request=request,
                name="account_exists.html",
                context={
                    "member": member,
                    "account_type": account_type
                }
            )

    return templates.TemplateResponse(
        request=request,
        name="review.html",
        context={
            "member_id": member_id,
            "account_type": account_type,
            "opening_deposit": opening_deposit
        }
    )


# Complete the demo account request after review
@app.post("/new-account/submit", response_class=HTMLResponse)
async def submit_new_account(
    request: Request,
    member_id: str = Form(...),
    account_type: str = Form(...),
    opening_deposit: float = Form(...)
):
    return templates.TemplateResponse(
        request=request,
        name="confirmation.html",
        context={
            "member_id": member_id.strip(),
            "account_type": account_type,
            "opening_deposit": opening_deposit
        }
    )