
import json
import urllib.request
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# Keep your existing three complete URLs here.
ORDERS_URL = "https://exam.sanand.workers.dev/questionData?email=22f3001026%40ds.study.iitm.ac.in&quizSign=iQS28QdKEbjAZzeMTGF2878B9zK4CQfmME%2BMLdzQeDzgBF%2BoDVnUMfr0f3AjbdN7VVu6EX8Op6nvTkIOxyUomyF5feRMcL546URzHhTAscfOv2iUixR77ByAcOZ0jqmeB6tDyOFdmKcOMYwrP6yFacCXxOqeMcwnhskk%2B7MAO1hH2mVUAnRir0bVGSwotN61gq8eklPj9Y4v5cLz7DgZzGNx%2FtM8Oje6LFYlM1dczwB%2Bo0XUmhyv0WfNzqsUqNRKKOiZuY98FCRdtc7os2dc24XZGvBFOKuT63HtBIRh7m470Ap7cLLcHoAH2uYL5r%2B%2FwCLpL8VY2SFG%2B7DgV44K0Q%3D%3D&questionId=q-ledger-agent-server&path=%2Forders&page=1"
RATES_URL = "https://exam.sanand.workers.dev/questionData?email=22f3001026%40ds.study.iitm.ac.in&quizSign=iQS28QdKEbjAZzeMTGF2878B9zK4CQfmME%2BMLdzQeDzgBF%2BoDVnUMfr0f3AjbdN7VVu6EX8Op6nvTkIOxyUomyF5feRMcL546URzHhTAscfOv2iUixR77ByAcOZ0jqmeB6tDyOFdmKcOMYwrP6yFacCXxOqeMcwnhskk%2B7MAO1hH2mVUAnRir0bVGSwotN61gq8eklPj9Y4v5cLz7DgZzGNx%2FtM8Oje6LFYlM1dczwB%2Bo0XUmhyv0WfNzqsUqNRKKOiZuY98FCRdtc7os2dc24XZGvBFOKuT63HtBIRh7m470Ap7cLLcHoAH2uYL5r%2B%2FwCLpL8VY2SFG%2B7DgV44K0Q%3D%3D&questionId=q-ledger-agent-server&path=%2Frates"
EXPORT_URL = "https://exam.sanand.workers.dev/questionData?email=22f3001026%40ds.study.iitm.ac.in&quizSign=iQS28QdKEbjAZzeMTGF2878B9zK4CQfmME%2BMLdzQeDzgBF%2BoDVnUMfr0f3AjbdN7VVu6EX8Op6nvTkIOxyUomyF5feRMcL546URzHhTAscfOv2iUixR77ByAcOZ0jqmeB6tDyOFdmKcOMYwrP6yFacCXxOqeMcwnhskk%2B7MAO1hH2mVUAnRir0bVGSwotN61gq8eklPj9Y4v5cLz7DgZzGNx%2FtM8Oje6LFYlM1dczwB%2Bo0XUmhyv0WfNzqsUqNRKKOiZuY98FCRdtc7os2dc24XZGvBFOKuT63HtBIRh7m470Ap7cLLcHoAH2uYL5r%2B%2FwCLpL8VY2SFG%2B7DgV44K0Q%3D%3D&questionId=q-ledger-agent-server&path=%2Fexport"


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
    # The export endpoint returns JSONL records.
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "orders" in data:
        return data["orders"]
    return []


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
    if order_id not in latest:
        latest[order_id] = (updated, order)
    elif updated > latest[order_id][0]:
        latest[order_id] = (updated, order)

orders = [item[1] for item in latest.values()]


def amount_usd(order):
    amount = Decimal(str(order["amount"]))
    rate = rates[order["currency"]]
    return amount * rate


class Question(BaseModel):
    question: str


@app.get("/")
def health():
    return {"status": "ok", "orders_loaded": len(orders)}


@app.post("/")
def answer_question(payload: Question):
    question = payload.question.lower()

    # Determine a date range if a month and year are present.
    months = {
        "january": 1, "february": 2, "march": 3,
        "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9,
        "october": 10, "november": 11, "december": 12
    }

    month = next(
        (num for name, num in months.items() if name in question),
        None
    )

    year = None
    for possible_year in range(2000, 2101):
        if str(possible_year) in question:
            year = possible_year
            break

    filtered = orders[:]

    # Revenue includes only currently paid orders.
    if any(word in question for word in [
        "revenue", "sales", "sold", "income"
    ]):
        filtered = [
            o for o in filtered
            if o["status"].lower() == "paid"
        ]

    # Filter by region.
    for region in ["north", "south", "east", "west"]:
        if region in question:
            filtered = [
                o for o in filtered
                if o["region"].lower() == region
            ]
            break

    # Filter by month/year using the business date in India.
    if month or year:
        filtered = [
            o for o in filtered
            if (
                (dt := datetime.fromisoformat(
                    o["created_at"].replace("Z", "+00:00")
                ).astimezone().strftime("%Y-%m"))
                and (not month or int(dt[5:7]) == month)
                and (not year or int(dt[:4]) == year)
            )
        ]

    # Product questions.
    product_names = sorted(
        {o["product"] for o in orders},
        key=len,
        reverse=True
    )
    product = next(
        (p for p in product_names if p.lower() in question),
        None
    )

    if product:
        filtered = [
            o for o in filtered
            if o["product"] == product
        ]

    if "revenue" in question or "sales" in question:
        total = sum(
            (amount_usd(o) for o in filtered),
            Decimal("0")
        )
        result = total.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return {"answer": float(result)}

    if "refund" in question:
        refunded = [
            o for o in orders
            if o["status"].lower() == "refunded"
        ]
        if month or year:
            refunded = [
                o for o in refunded
                if (
                    (dt := datetime.fromisoformat(
                        o["created_at"].replace("Z", "+00:00")
                    ).astimezone().strftime("%Y-%m"))
                    and (not month or int(dt[5:7]) == month)
                    and (not year or int(dt[:4]) == year)
                )
            ]
        total = sum(
            (amount_usd(o) for o in refunded),
            Decimal("0")
        )
        return {
            "answer": float(total.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ))
        }

    if "count" in question or "how many" in question:
        return {"answer": len(filtered)}

    if "product" in question:
        totals = {}
        for o in filtered:
            totals[o["product"]] = (
                totals.get(o["product"], Decimal("0"))
                + amount_usd(o)
            )
        if totals:
            best = max(totals, key=totals.get)
            return {"answer": best}

    if "customer" in question:
        customers = {o["customer"] for o in filtered}
        if "how many" in question or "count" in question:
            return {"answer": len(customers)}

    return {"answer": "Unable to determine the answer"}
