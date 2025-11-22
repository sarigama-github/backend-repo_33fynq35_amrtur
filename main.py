import os
from typing import List, Optional, Literal
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Customer, Product, Order, OrderItem, AnalyticsEvent, SupportTicket

app = FastAPI(title="Coral Shopping API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Coral Shopping Backend Running"}


# ---- Schemas Endpoint (for viewer/tools) ----
@app.get("/schema")
def get_schema():
    return {
        "collections": [
            "customer",
            "product",
            "order",
            "supportticket",
            "analyticsevent",
        ]
    }


# ---- Customers ----
class CreateCustomerRequest(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None


@app.post("/customers")
def create_customer(payload: CreateCustomerRequest):
    data = Customer(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        addresses=[payload.address] if payload.address else [],
    )
    inserted_id = create_document("customer", data)
    return {"id": inserted_id}


@app.get("/customers")
def list_customers(limit: int = 50):
    docs = get_documents("customer", {}, limit)
    for d in docs:
        d["_id"] = str(d["_id"])  # serialize
    return {"items": docs}


# ---- Products ----
class CreateProductRequest(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: Literal['foodstuffs', 'gifts', 'hampers', 'household', 'office']
    images: Optional[List[str]] = []
    in_stock: bool = True
    stock_qty: Optional[int] = 0
    tags: Optional[List[str]] = []


@app.post("/products")
def create_product(payload: CreateProductRequest):
    data = Product(**payload.model_dump())
    inserted_id = create_document("product", data)
    return {"id": inserted_id}


@app.get("/products")
def get_products(
    category: Optional[str] = None,
    q: Optional[str] = None,
    minPrice: Optional[float] = Query(None, ge=0),
    maxPrice: Optional[float] = Query(None, ge=0),
    limit: int = 50,
):
    filter_dict: dict = {}
    if category:
        filter_dict["category"] = category
    if minPrice is not None or maxPrice is not None:
        price_filter = {}
        if minPrice is not None:
            price_filter["$gte"] = float(minPrice)
        if maxPrice is not None:
            price_filter["$lte"] = float(maxPrice)
        filter_dict["price"] = price_filter
    if q:
        # simple text search on title/description
        filter_dict["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"tags": {"$regex": q, "$options": "i"}},
        ]

    docs = get_documents("product", filter_dict, limit)
    for d in docs:
        d["_id"] = str(d["_id"])  # serialize
    return {"items": docs}


# ---- AI-like Recommendations (rule-based MVP) ----
class RecommendationRequest(BaseModel):
    budget_min: Optional[float] = 0
    budget_max: Optional[float] = None
    preferences: Optional[List[str]] = None  # categories or tags


@app.post("/recommendations")
def get_recommendations(req: RecommendationRequest):
    filter_dict: dict = {}
    if req.budget_min is not None or req.budget_max is not None:
        price_filter = {}
        if req.budget_min is not None:
            price_filter["$gte"] = float(req.budget_min)
        if req.budget_max is not None:
            price_filter["$lte"] = float(req.budget_max)
        filter_dict["price"] = price_filter

    if req.preferences:
        filter_dict["$or"] = [
            {"category": {"$in": req.preferences}},
            {"tags": {"$in": req.preferences}},
        ]

    items = get_documents("product", filter_dict, 24)
    # naive sort for "value" - lowest price first
    items.sort(key=lambda x: (x.get("price", 0), -x.get("rating", 0)))
    for d in items:
        d["_id"] = str(d["_id"])  # serialize
    return {"items": items}


# ---- Comparison ----
class CompareRequest(BaseModel):
    ids: List[str]


@app.post("/compare")
def compare_products(req: CompareRequest):
    from bson import ObjectId
    ids = [ObjectId(x) for x in req.ids]
    docs = list(db["product"].find({"_id": {"$in": ids}}))
    for d in docs:
        d["_id"] = str(d["_id"])  # serialize
    return {"items": docs}


# ---- Orders ----
class CreateOrderRequest(BaseModel):
    customer_id: str
    items: List[OrderItem]
    delivery_option: Literal['pickup', 'delivery'] = 'delivery'
    delivery_address: Optional[str] = None
    notes: Optional[str] = None


@app.post("/orders")
def create_order(req: CreateOrderRequest):
    # compute totals
    subtotal = sum([it.unit_price * it.quantity for it in req.items])
    shipping_fee = 1200 if req.delivery_option == 'delivery' else 0
    total = subtotal + shipping_fee

    order = Order(
        customer_id=req.customer_id,
        items=req.items,
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        total=total,
        payment_method='bank_transfer',
        payment_status='pending',
        status='pending',
        delivery_option=req.delivery_option,
        delivery_address=req.delivery_address,
        notes=req.notes,
    )

    inserted_id = create_document("order", order)
    return {
        "id": inserted_id,
        "bank_transfer_instructions": {
            "account_name": "Coral Shopping LTD",
            "bank": "GTBank",
            "account_number": "0123456789",
            "amount": total,
            "narration": f"ORDER-{inserted_id[:6].upper()}"
        }
    }


@app.get("/orders")
def list_orders(customer_id: Optional[str] = None, limit: int = 50):
    filter_dict = {"customer_id": customer_id} if customer_id else {}
    docs = get_documents("order", filter_dict, limit)
    for d in docs:
        d["_id"] = str(d["_id"])  # serialize
    return {"items": docs}


# ---- Analytics ----
@app.post("/analytics")
def track_event(event: AnalyticsEvent):
    create_document("analyticsevent", event)
    return {"status": "ok"}


# ---- Support Tickets ----
@app.post("/support")
def open_ticket(ticket: SupportTicket):
    inserted_id = create_document("supportticket", ticket)
    return {"id": inserted_id}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
