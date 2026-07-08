import time
import uuid
import jwt
import os
import yaml
from fastapi import FastAPI, Query, HTTPException, Request, Header
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# ==========================================
# UNIVERSAL CONFIGURATION & GLOBAL VARIABLES
# ==========================================
EMAIL = "22f3002107@ds.study.iitm.ac.in"
ALLOWED_ORIGIN_Q1 = "https://dash-1tn584.example.com"
ASSIGNED_API_KEY = "ak_tmfzws5hv0d43iojh0bna2as"  # Assigned API key for analytics
START_TIME = time.time()
LOG_BUFFER = []
REQUEST_COUNTER = {"http_requests_total": 0}
# --- GLOBAL VARIABLES FOR QUESTION 9 ---
TOTAL_ORDERS = 45
ASSIGNED_RATE_LIMIT = 18
RATE_LIMIT_WINDOW = 10.0

# Fixed orders catalog generate karein (1 to 45)
ORDERS_CATALOG = [
    {"id": i, "item": f"Item-{i}", "quantity": (i * 3) % 10 + 1}
    for i in range(1, TOTAL_ORDERS + 1)
]

IDEMPOTENCY_STORE = {}  # {key: {"id": order_id, "response": data}}
RATE_LIMIT_STORE = {}   # {client_id: [timestamps]}



# Q2 OIDC Config
ISSUER_Q2 = "https://idp.exam.local"
AUDIENCE_Q2 = "tds-rvi1vjkn.apps.exam.local"
PUBLIC_KEY_Q2 = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2okOHspNjgA+2rTLbeuY
cxiP/hG8C6Sb9iwg3yiLAA4HCnpITcbWCSelbvbYGuc3EbNy4xFyf5Cbj5DHJMID
EkryOgyd2giIIIBOUBj8S63uGcnRpOBh9NFatfNwheKuzsPuVNldu6A9cNteNpXc
WyJjG2axVfmq7i6SuKr1JoWYG7xTTAvKPujSl4OtsQfO3h5NepzdfXpr28oNnzfW
ed+zclR6BcmNNo/WVfJ4xyCLSf0BCOgdTgW6PdaChd1l9VDetJZVEgC5tkyvXsfI
SI6iyrYbKR0NEBSqq4XkadEjsCs4F1RncsS4LlgniT7GlkL9Mce3b0wGLs9/7ZIX
dQIDAQAB
-----END PUBLIC KEY-----"""

# Q3 Hardcoded Layer 1 Defaults
DEFAULTS_Q3 = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000"
}

# ------------------------------------------
# DATA MODELS
# ------------------------------------------
class StatsResponse(BaseModel):
    email: str
    count: int
    sum: int
    min: int
    max: int
    mean: float

class TokenRequest(BaseModel):
    token: str

# --- NEW MODELS FOR ANALYTICS ---
class Event(BaseModel):
    user: str
    amount: float
    ts: int

class AnalyticsRequest(BaseModel):
    events: List[Event]

# ------------------------------------------
# PATH-AWARE MIDDLEWARE (CORS & SYSTEM HEADERS)
# ------------------------------------------
@app.middleware("http")
async def global_middleware_handler(request: Request, call_next):
    # --- Q6: Prometheus Counter Increment ---
    REQUEST_COUNTER["http_requests_total"] += 1
    
    start_time = time.time()
    request_id = str(uuid.uuid4())
    origin = request.headers.get("origin") or request.headers.get("Origin") or ""
    path = request.url.path

    # --- Q6: Structured Logging Buffer ---
    if not path.startswith("/logs/tail"):
        LOG_BUFFER.append({
            "level": "INFO",
            "ts": int(time.time()),
            "path": path,
            "request_id": request_id
        })
        if len(LOG_BUFFER) > 500:
            LOG_BUFFER.pop(0)

    if request.method == "OPTIONS":
        response = Response(status_code=200)
        if path.startswith("/stats"):
            if origin == ALLOWED_ORIGIN_Q1:
                response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN_Q1
                response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "*"
            else:
                response.status_code = 400
                return response
        else:
            response.headers["Access-Control-Allow-Origin"] = origin if origin else "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
        
        process_time = time.time() - start_time
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.6f}"
        return response

    response = await call_next(request)
    if path.startswith("/stats"):
        if origin == ALLOWED_ORIGIN_Q1:
            response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN_Q1
    else:
        response.headers["Access-Control-Allow-Origin"] = origin if origin else "*"

    process_time = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.6f}"
    
    return response

# ------------------------------------------
# ENDPOINT: QUESTION 1 (GET /stats)
# ------------------------------------------
@app.get("/stats", response_model=StatsResponse)
async def get_stats(values: str = Query(..., description="Comma-separated list of integers")):
    try:
        int_values = [int(x.strip()) for x in values.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid input. Please provide comma-separated integers.")
    
    if not int_values:
        raise HTTPException(status_code=400, detail="Values list cannot be empty.")
    
    count = len(int_values)
    total_sum = sum(int_values)
    min_val = min(int_values)
    max_val = max(int_values)
    mean_val = round(total_sum / count, 4)
    
    return {
        "email": EMAIL,
        "count": count,
        "sum": total_sum,
        "min": min_val,
        "max": max_val,
        "mean": mean_val
    }

# ------------------------------------------
# ENDPOINT: QUESTION 2 (POST /verify)
# ------------------------------------------
@app.post("/")
@app.post("/verify")
async def verify_token(data: TokenRequest):
    try:
        payload = jwt.decode(
            data.token,
            PUBLIC_KEY_Q2,
            algorithms=["RS256"],
            audience=AUDIENCE_Q2,
            issuer=ISSUER_Q2,
            leeway=120,
            options={"require": ["exp", "iss", "aud", "sub"]}
        )
        return {
            "valid": True,
            "email": payload.get("email"),
            "sub": payload.get("sub"),
            "aud": payload.get("aud")
        }
    except Exception:
        return JSONResponse(status_code=401, content={"valid": False})

# ------------------------------------------
# ENDPOINT: QUESTION 3 (GET /effective-config)
# ------------------------------------------
def coerce_value(key: str, val):
    if val is None:
        return None
    val_str = str(val).strip()
    if key in ["port", "workers"]:
        try:
            return int(val_str)
        except ValueError:
            return val
    if key == "debug":
        return val_str.lower() in ["true", "1", "yes", "on"]
    return val_str

@app.get("/effective-config")
async def get_effective_config(request: Request):
    current_config = DEFAULTS_Q3.copy()
    
    yaml_path = "config.development.yaml"
    if os.path.exists(yaml_path):
        try:
            with open(yaml_path, "r") as f:
                yaml_data = yaml.safe_load(f)
                if isinstance(yaml_data, dict):
                    for k, v in yaml_data.items():
                        if k in current_config:
                            current_config[k] = v
        except Exception:
            pass
            
    env_file_path = ".env"
    if os.path.exists(env_file_path):
        try:
            with open(env_file_path, "r") as f:
                for line in f:
                    cleaned_line = line.strip()
                    if cleaned_line and not cleaned_line.startswith("#") and "=" in cleaned_line:
                        k_raw, v_raw = cleaned_line.split("=", 1)
                        key = k_raw.strip()
                        val = v_raw.strip().strip("'\"")
                        
                        if key == "NUM_WORKERS":
                            current_config["workers"] = val
                        elif key.startswith("APP_"):
                            actual_key = key[4:].lower()
                            if actual_key in current_config:
                                current_config[actual_key] = val
        except Exception:
            pass

    for key, val in os.environ.items():
        if key == "NUM_WORKERS":
            current_config["workers"] = val
        elif key.startswith("APP_"):
            actual_key = key[4:].lower().lstrip("_")
            if actual_key in current_config:
                current_config[actual_key] = val

    query_params = request.query_params.multi_items()
    for raw_k, raw_v in query_params:
        if raw_k == "set" and "=" in raw_v:
            k, v = raw_v.split("=", 1)
            if k in current_config:
                current_config[k] = v
        elif raw_k.startswith("set="):
            pair = raw_k[4:]
            if "=" in pair:
                k, v = pair.split("=", 1)
                if k in current_config:
                    current_config[k] = v
        elif raw_k in current_config:
            current_config[raw_k] = raw_v

    final_output = {}
    for k, v in current_config.items():
        final_output[k] = coerce_value(k, v)

    final_output["api_key"] = "****"
    
    return final_output

# ------------------------------------------
# NEW ENDPOINT: DEPLOY POST /analytics
# ------------------------------------------
@app.post("/analytics")
async def post_analytics(request: AnalyticsRequest, x_api_key: Optional[str] = Header(None)):
    # 1. API Key Authentication Check (Header validation)
    if not x_api_key or x_api_key != ASSIGNED_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized: Missing or invalid API key.")

    events = request.events
    total_events = len(events)
    unique_users = set()
    revenue = 0.0
    user_revenue_map = {}

    # 2. Aggregation & Filter Logic
    for event in events:
        if event.user:
            unique_users.add(event.user)
        
        # Rule: Only aggregate revenue and user totals where amount > 0
        if event.amount > 0:
            revenue += event.amount
            user_revenue_map[event.user] = user_revenue_map.get(event.user, 0.0) + event.amount

    # Rule: Find the top user with the highest positive-amount total
    top_user = ""
    max_revenue = -1.0
    for user, user_total in user_revenue_map.items():
        if user_total > max_revenue:
            max_revenue = user_total
            top_user = user

    # 3. Formatted JSON Response
    return {
        "email": EMAIL,
        "total_events": total_events,
        "unique_users": len(unique_users),
        "revenue": round(revenue, 2),  # Prevents floating point issues
        "top_user": top_user
    }
# ==========================================
# ENDPOINTS: QUESTION 6 (OBSERVABILITY)
# ==========================================
@app.get("/work")
async def do_work(n: int = Query(...)):
    return {"email": EMAIL, "done": n}

@app.get("/metrics")
async def get_metrics():
    val = REQUEST_COUNTER["http_requests_total"]
    data = f"# HELP http_requests_total Total\n# TYPE http_requests_total counter\nhttp_requests_total {val}\n"
    return Response(content=data, media_type="text/plain")

@app.get("/healthz")
async def get_healthz():
    return {"status": "ok", "uptime_s": float(time.time() - START_TIME)}

@app.get("/logs/tail")
async def get_logs_tail(limit: int = Query(...)):
    return LOG_BUFFER[-limit:] if limit > 0 else []
# ==========================================
# DATA MODELS FOR QUESTION 8 (EXTRACTION)
# ==========================================
class ExtractRequest(BaseModel):
    text: str

class InvoiceResponse(BaseModel):
    vendor: str
    amount: float
    currency: str
    date: str

# ==========================================
# ENDPOINT: QUESTION 8 (POST /extract)
# ==========================================
import httpx
import json

@app.post("/extract", response_model=InvoiceResponse)
async def extract_invoice(payload: ExtractRequest):
    if not payload.text or len(payload.text.strip()) < 5:
        raise HTTPException(status_code=422, detail="Invalid text input")

    # Strict Zero-Temperature Prompt taaki Llama sirf raw structured JSON de
    system_instruction = (
        "You are a strict data extraction tool. Extract fields from the invoice text. "
        "Respond ONLY with a valid JSON object matching this schema exactly:\n"
        '{"vendor": "string", "amount": number, "currency": "3-letter uppercase string", "date": "YYYY-MM-DD"}\n'
        "Do not include markdown blocks, backticks, or any conversational text. Only raw JSON."
    )

    # CONNECTING RENDER TO YOUR LAPTOP VIA NGROK TUNNEL
    TUNNEL_URL = "https://ngrok-free.app"

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                TUNNEL_URL,
                json={
                    "model": "llama3.2",
                    "messages": [
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": payload.text}
                    ],
                    "temperature": 0.0,
                    "stream": False
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=422, detail="LLM extraction failed")
                
            res_data = response.json()
            # FIX: [0] index add kiya gaya hai list parsing ke liye
            llm_content = res_data["choices"][0]["message"]["content"].strip()
            
            # Agar model markdown backticks use kare toh use clean karna
            if llm_content.startswith("```"):
                llm_content = llm_content.strip("`").replace("json", "", 1).strip()
            
            extracted_json = json.loads(llm_content)
            
            return InvoiceResponse(
                vendor=str(extracted_json.get("vendor", "Unknown")),
                amount=float(extracted_json.get("amount", 0.0)),
                currency=str(extracted_json.get("currency", "USD")).upper(),
                date=str(extracted_json.get("date", "2026-01-01"))
            )
            
    except Exception:
        raise HTTPException(status_code=422, detail="Unprocessable invoice formatting")

# ------------------------------------------
# DATA MODELS FOR QUESTION 9 (ORDERS API)
# ------------------------------------------
class OrderCreateRequest(BaseModel):
    item: Optional[str] = "Default Item"
    quantity: Optional[int] = 1

# ==========================================
# ENDPOINTS: QUESTION 9 (ORDERS API)
# ==========================================

def check_rate_limit(client_id: str):
    if not client_id:
        return None
    current_time = time.time()
    if client_id not in RATE_LIMIT_STORE:
        RATE_LIMIT_STORE[client_id] = []
    
    # 10 seconds se purane records ko saaf karein
    RATE_LIMIT_STORE[client_id] = [t for t in RATE_LIMIT_STORE[client_id] if current_time - t < RATE_LIMIT_WINDOW]
    
    if len(RATE_LIMIT_STORE[client_id]) >= ASSIGNED_RATE_LIMIT:
        # Strict Header Compliance using direct JSONResponse JSON structures
        return JSONResponse(
            status_code=429,
            content={"detail": "Too Many Requests"},
            headers={"Retry-After": "10", "Access-Control-Allow-Origin": "*"}
        )
    RATE_LIMIT_STORE[client_id].append(current_time)
    return None

# 1. POST /orders (Idempotent creation)
@app.post("/orders", status_code=201)
async def create_order(
    payload: Optional[OrderCreateRequest] = None,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_client_id: Optional[str] = Header(None, alias="X-Client-Id")
):
    if x_client_id:
        limit_check = check_rate_limit(x_client_id)
        if limit_check: # Triggered strict 429 payload instantly
            return limit_check

    if idempotency_key and idempotency_key in IDEMPOTENCY_STORE:
        return IDEMPOTENCY_STORE[idempotency_key]

    item_name = payload.item if (payload and payload.item) else "Item-Mock"
    item_qty = payload.quantity if (payload and payload.quantity) else 1

    new_order_id = int(time.time() * 1000) % 1000000
    order_data = {
        "id": new_order_id,
        "item": item_name,
        "quantity": item_qty,
        "status": "created"
    }

    if idempotency_key:
        IDEMPOTENCY_STORE[idempotency_key] = order_data

    return order_data

# 2. GET /orders (Cursor-based Pagination)
@app.get("/orders")
async def get_orders(
    limit: int = Query(10, ge=1),
    cursor: Optional[str] = Query(None),
    x_client_id: Optional[str] = Header(None, alias="X-Client-Id")
):
    if x_client_id:
        limit_check = check_rate_limit(x_client_id)
        if limit_check:
            return limit_check

    start_index = 0
    if cursor:
        try:
            start_index = int(cursor)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cursor")

    sliced_items = ORDERS_CATALOG[start_index : start_index + limit]
    next_index = start_index + len(sliced_items)
    next_cursor = str(next_index) if next_index < TOTAL_ORDERS else None

    return {
        "items": sliced_items,
        "next_cursor": next_cursor
    }
