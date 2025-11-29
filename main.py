import os
import io
import json
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv
from pdf2image import convert_from_bytes
from PIL import Image
from difflib import SequenceMatcher
import requests

# -----------------------------
# GOOGLE GENAI V1 CLIENT
# -----------------------------
from google.genai import Client

load_dotenv()

GENAI_API_KEY = os.getenv("GENAI_API_KEY")
GENAI_MODEL = os.getenv("GENAI_MODEL", "gemini-2.5-flash")

if not GENAI_API_KEY:
    raise RuntimeError("GENAI_API_KEY not found")

client = Client(api_key=GENAI_API_KEY)

# ==============================================================
#                  REQUEST + RESPONSE MODELS
# ==============================================================

class ExtractRequest(BaseModel):
    document: HttpUrl


class BillItem(BaseModel):
    item_name: str
    item_amount: float
    item_rate: float
    item_quantity: float


class PageLineItems(BaseModel):
    page_no: int
    page_type: str
    bill_items: List[BillItem]


class TokenUsage(BaseModel):
    total_tokens: int
    input_tokens: int
    output_tokens: int


class ExtractData(BaseModel):
    pagewise_line_items: List[PageLineItems]
    total_item_count: int


class ExtractResponse(BaseModel):
    is_success: bool
    token_usage: TokenUsage
    data: ExtractData


# ==============================================================
#                        HELPERS
# ==============================================================

def download_document(url: str) -> bytes:
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return r.content
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download document: {e}")


def pdf_or_image_to_pages(file_bytes: bytes, url: str):
    url = str(url).lower()  # FIXED

    try:
        if url.endswith(".pdf"):
            return convert_from_bytes(file_bytes)
        else:
            img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            return [img]
    except:
        # fallback to PDF conversion then image
        try:
            return convert_from_bytes(file_bytes)
        except:
            img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            return [img]


def find_json(text: str):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise HTTPException(status_code=500, detail="Gemini output contains no JSON")
    try:
        return json.loads(text[start:end + 1])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JSON parsing failed: {e}")


def call_gemini_page(img: Image.Image):
    prompt = """
Extract all line items from this invoice page.

Return STRICT JSON ONLY:
{
  "page_type": "Bill Detail | Final Bill | Pharmacy",
  "items": [
    {
      "item_name": "string",
      "quantity": 0,
      "rate": 0,
      "amount": 0
    }
  ]
}

Rules:
- numbers must be raw floats
- do not include totals or subtotals as items
- respond with pure JSON and nothing else
"""

    res = client.models.generate_content(
        model=GENAI_MODEL,
        contents=[prompt, img]
    )

    data = find_json(res.text)

    usage = getattr(res, "usage_metadata", None)

    total_tokens = getattr(usage, "total_token_count", 0) if usage else 0
    input_tokens = getattr(usage, "input_token_count", 0) if usage else 0
    output_tokens = getattr(usage, "output_token_count", 0) if usage else 0

    return data, total_tokens, input_tokens, output_tokens


def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def dedupe_items(items, threshold=0.92, tol=1.0):
    unique = []
    for it in items:
        duplicate = False
        for u in unique:
            if similarity(it["item_name"], u["item_name"]) >= threshold and abs(it["item_amount"] - u["item_amount"]) <= tol:
                duplicate = True
                break
        if not duplicate:
            unique.append(it)
    return unique


# ==============================================================
#                 MAIN EXTRACTION PIPELINE
# ==============================================================

def extract_from_document(file_bytes: bytes, url: str):
    pages = pdf_or_image_to_pages(file_bytes, url)

    all_items = []
    pagewise_output = []

    total_tokens = 0
    input_tokens = 0
    output_tokens = 0

    for page_no, img in enumerate(pages, start=1):
        data, t, i, o = call_gemini_page(img)

        total_tokens += t
        input_tokens += i
        output_tokens += o

        page_items = []

        for item in data.get("items", []):
            try:
                itm = {
                    "item_name": item["item_name"],
                    "item_amount": float(item["amount"]),
                    "item_rate": float(item["rate"]),
                    "item_quantity": float(item["quantity"])
                }
                all_items.append(itm)
                page_items.append(itm)
            except:
                continue

        pagewise_output.append({
            "page_no": page_no,
            "page_type": data.get("page_type", "Bill Detail"),
            "bill_items": page_items
        })

    unique_items = dedupe_items(all_items)
    total_item_count = len(unique_items)

    return pagewise_output, unique_items, total_item_count, total_tokens, input_tokens, output_tokens


# ==============================================================
#                        FASTAPI APP
# ==============================================================

app = FastAPI(title="HackRx Bill Extraction API", version="1.0")

@app.get("/")
def home():
    return {"status": "running"}


@app.post("/extract-bill-data", response_model=ExtractResponse)
def extract_bill(req: ExtractRequest):
    raw = download_document(req.document)

    pages, unique_items, total_count, tt, it, ot = extract_from_document(raw, req.document)

    return ExtractResponse(
        is_success=True,
        token_usage=TokenUsage(
            total_tokens=tt,
            input_tokens=it,
            output_tokens=ot
        ),
        data=ExtractData(
            pagewise_line_items=pages,
            total_item_count=total_count
        )
    )
