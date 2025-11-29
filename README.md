🚀 HackRx Bill Extraction API — README.md
# 🧾 HackRx Bill Extraction API
A FastAPI-based solution for automated extraction of **line items, totals, and bill summaries** from PDF and image invoices using **Gemini 2.5 Flash**.  
Built for the **HackRx Datathon** challenge.

---

## 🔗 Live API (Hosted on Render)

**Base URL:**  


https://bfhl-datathon.onrender.com


### 📌 Primary Endpoint (HackRx Webhook)



POST /api/v1/hackrx/run


This endpoint matches the **exact** request–response structure required by HackRx.

---

## 📥 Request Format (as per HackRx Specification)

### **POST** `/api/v1/hackrx/run`

```json
{
  "document": "https://public-url-to-invoice.pdf-or-image"
}


document must be a publicly accessible URL

Supports both PDFs and images (PNG/JPG)

📤 Response Format (as required by HackRx)

Sample Response:

{
  "is_success": true,
  "token_usage": {
    "total_tokens": 1234,
    "input_tokens": 0,
    "output_tokens": 0
  },
  "data": {
    "pagewise_line_items": [
      {
        "page_no": 1,
        "page_type": "Bill Detail",
        "bill_items": [
          {
            "item_name": "PARACETAMOL 500MG",
            "item_amount": 120.0,
            "item_rate": 60.0,
            "item_quantity": 2.0
          }
        ]
      }
    ],
    "total_item_count": 1
  }
}

🧠 How It Works
1️⃣ Document Fetching

Downloads the provided file from URL

Detects whether it is PDF or Image

2️⃣ Page Processing

PDFs are converted into images using pdf2image

Images are processed page-by-page

3️⃣ LLM Extraction (Gemini 2.5 Flash)

Each page is sent to Gemini using a strict JSON-only prompt:

Extract item name

Rate

Quantity

Final amount

Page type: Bill Detail | Final Bill | Pharmacy

4️⃣ De-duplication

Bills often repeat line items across summary/final pages.
We remove duplicates using:

Description similarity (SequenceMatcher)

Amount tolerance

5️⃣ Final Response Assembly

Per-page line items

Global deduplicated item count

Total token usage from Gemini

🧪 Local Development
Clone repository:
git clone <repo-url>
cd bfhl_datathon

Create a virtual environment:
python3 -m venv venv
source venv/bin/activate

Install dependencies:
pip install -r requirements.txt

Add environment variables in .env:
GENAI_API_KEY=AIzaSyA5nyRyQhrOQpubXCq0zIGi_1KWVyzMHm8
GENAI_MODEL=gemini-2.5-flash

Run FastAPI server:
uvicorn main:app --reload --host 0.0.0.0 --port 8000


Access docs at:

http://127.0.0.1:8000/docs

🌐 Deployment (Render.com)

This API is deployed on Render using:

uvicorn main:app --host 0.0.0.0 --port 10000


Environment variables are configured in Render dashboard.

📌 File Structure
.
├── main.py
├── requirements.txt
├── README.md
├── .env
└── venv/

🎯 Features Summary

✔ PDF & Image (JPG/PNG) support

✔ Multi-page invoice handling

✔ Gemini 2.5 Flash extraction

✔ Duplicate item detection

✔ Fully compliant HackRx JSON structure

✔ Token usage reporting

✔ Public, scalable deployment on Render

👨‍💻 Author

Akhilesh Kumar
NIT Srinagar
Backend Developer & AI Enthusiast


---
