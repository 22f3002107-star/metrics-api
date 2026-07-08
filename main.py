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

    
