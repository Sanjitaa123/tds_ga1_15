
import json
import urllib.request
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# Keep your existing three complete URLs here.
ORDERS_URL = "https://exam.sanand.workers.dev/questionData?email=22f3001026%40ds.study.iitm.ac.in&quizSign=iQS28QdKEbjAZzeMTGF2878B9zK4CQfmME%2BMLdzQeDzgBF%2BoDVnUMfr0f3AjbdN7VVu6EX8Op6nvTkIOxyUomyF5feRMcL546URzHhTAscfOv2iUixR77ByAcOZ0jqmeB6tDyOFdmKcOMYwrP6yFacCXxOqeMcwnhskk%2B7MAO1hH2mVUAnRir0bVGSwotN61gq8eklPj9Y4v5cLz7DgZzGNx%2FtM8Oje6LFYlM1dczwB%2Bo0XUmhyv0WfNzqsUqNRKKOiZuY98FCRdtc7os2dc24XZGvBFOKuT63HtBIRh7m470Ap7cLLcHoAH2uYL5r%2B%2FwCLpL8VY2SFG%2B7DgV44K0Q%3D%3D&questionId=q-ledger-agent-server&path=%2Forders&page=1"

RATES_URL = "https://exam.sanand.workers.dev/questionData?email=22f3001026%40ds.study.iitm.ac.in&quizSign=iQS28QdKEbjAZzeMTGF2878B9zK4CQfmME%2BMLdzQeDzgBF%2BoDVnUMfr0f3AjbdN7VVu6EX8Op6nvTkIOxyUomyF5feRMcL546URzHhTAscfOv2iUixR77ByAcOZ0jqmeB6tDyOFdmKcOMYwrP6yFacCXxOqeMcwnhskk%2B7MAO1hH2mVUAnRir0bVGSwotN61gq8eklPj9Y4v5cLz7DgZzGNx%2FtM8Oje6LFYlM1dczwB%2Bo0XUmhyv0WfNzqsUqNRKKOiZuY98FCRdtc7os2dc24XZGvBFOKuT63HtBIRh7m470Ap7cLLcHoAH2uYL5r%2B%2FwCLpL8VY2SFG%2B7DgV44K0Q%3D%3D&questionId=q-ledger-agent-server&path=%2Frates"

EXPORT_URL = "https://exam.sanand.workers.dev/questionData?email=22f3001026%40ds.study.iitm.ac.in&quizSign=iQS28QdKEbjAZzeMTGF2878B9zK4CQfmME%2BMLdzQeDzgBF%2BoDVnUMfr0f3AjbdN7VVu6EX8Op6nvTkIOxyUomyF5feRMcL546URzHhTAscfOv2iUixR77ByAcOZ0jqmeB6tDyOFdmKcOMYwrP6yFacCXxOqeMcwnhskk%2B7MAO1hH2mVUAnRir0bVGSwotN61gq8eklPj9Y4v5cLz7DgZzGNx%2FtM8Oje6LFYlM1dczwB%2Bo0XUmhyv0WfNzqsUqNRKKOiZuY98FCRdtc7os2dc24XZGvBFOKuT63HtBIRh7m470Ap7cLLcHoAH2uYL5r%2B%2FwCLpL8VY2SFG%2B7DgV44K0Q%3D%3D&questionId=q-ledger-agent-server&path=%2Fexport"

IST = ZoneInfo("Asia/Kolkata")


def fetch_data(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }
    )

    with urllib.request.urlopen(req, timeout=20) as response:
        text = response.read().decode("utf-8").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return [
            json.loads(line)
            for line in text.splitlines()
            if line.strip()
        ]


def get_orders(data):
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        if isinstance(data.get("orders"), list):
            return data["orders"]

        # Handle a single order returned as a JSON object.
        if "id" in data and "updated_at" in data:
            return [data]

    return []


# Load data once when the service starts.
raw = fetch_data(EXPORT_URL)
orders = get_orders(raw)

rate_data = fetch_data(RATES_URL)
rates = {
    key: Decimal(str(value))
    for key, value in rate_data["usd_per_unit"].items()
}


# Keep only the latest version of each order.
latest = {}

for order in orders:
    order_id = order["id"]
    updated = datetime.fromisoformat(
        order["updated_at"].replace("Z", "+00:00")
    )

    if (
        order_id not in latest
        or updated > latest[order_id][0]
    ):
        latest[order_id] = (updated, order)

orders = [item[1] for item in latest.values()]


def amount_usd(order):
    amount = Decimal(str(order["amount"]))
    rate = rates[order["currency"]]
    return amount * rate


def business_month(order):
    dt = datetime.fromisoformat(
        order["created_at"].replace("Z", "+00:00")
    )
    return dt.astimezone(IST).strftime("%Y-%m")


class Question(BaseModel):
    question: str


@app.get("/")
def health():
    return {
        "status": "ok",
        "orders_loaded": len(orders)
    }


@app.post("/")
def answer_question(payload: Question):
    question = payload.question.lower()

    months = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12
    }

    month = next(
        (
            num for name, num in months.items()
            if name in question
        ),
        None
    )

    year = None

    for possible_year in range(2000, 2101):
        if str(possible_year) in question:
            year = possible_year
            break

    filtered = orders[:]

    # Apply month/year filters using Asia/Kolkata time.
    if month is not None or year is not None:
        filtered = [
            order for order in filtered
            if (
                (month is None
                 or int(business_month(order)[5:7]) == month)
                and
                (year is None
                 or int(business_month(order)[:4]) == year)
            )
        ]

    # Filter by region.
    for region in ["north", "south", "east", "west"]:
        if region in question:
            filtered = [
                order for order in filtered
                if str(order.get("region", "")).lower() == region
            ]
            break

    # Identify a product mentioned in the question.
    product_names = sorted(
        {
            order["product"]
            for order in orders
            if order.get("product")
        },
        key=len,
        reverse=True
    )

    product = next(
        (
            name for name in product_names
            if name.lower() in question
        ),
        None
    )

    if product is not None:
        filtered = [
            order for order in filtered
            if order.get("product") == product
        ]

    # Customer counts must be checked before general order counts.
    if "customer" in question and (
        "how many" in question or "count" in question
    ):
        customers = {
            order["customer"]
            for order in filtered
            if order.get("customer") is not None
        }
        return {"answer": len(customers)}

    # Refund calculations use refunded orders and all active filters.
    if "refund" in question:
        refunded = [
            order for order in filtered
            if str(order.get("status", "")).lower() == "refunded"
        ]

        total = sum(
            (amount_usd(order) for order in refunded),
            Decimal("0")
        )

        result = total.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        return {"answer": float(result)}

    # Revenue and sales include only currently paid orders.
    if any(
        word in question
        for word in ["revenue", "sales", "income"]
    ):
        paid = [
            order for order in filtered
            if str(order.get("status", "")).lower() == "paid"
        ]

        total = sum(
            (amount_usd(order) for order in paid),
            Decimal("0")
        )

        result = total.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        return {"answer": float(result)}

    # Count orders, not distinct customers.
    if "count" in question or "how many" in question:
        return {"answer": len(filtered)}

    # Product with the highest revenue or sales amount.
    if "product" in question:
        if "revenue" in question or "sales" in question:
            totals = {}

            for order in filtered:
                if str(order.get("status", "")).lower() != "paid":
                    continue

                name = order["product"]
                totals[name] = (
                    totals.get(name, Decimal("0"))
                    + amount_usd(order)
                )

            if totals:
                return {
                    "answer": max(totals, key=totals.get)
                }

        # Otherwise, find the product with the most orders.
        counts = {}

        for order in filtered:
            name = order["product"]
            counts[name] = counts.get(name, 0) + 1

        if counts:
            return {
                "answer": max(counts, key=counts.get)
            }

    return {
        "answer": "Unable to determine the answer"
    }
