import time
import uuid
import jwt
import os
import yaml
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel

app = FastAPI()

# ==========================================
# UNIVERSAL CONFIGURATION & GLOBAL VARIABLES
# ==========================================
EMAIL = "22f3002107@ds.study.iitm.ac.in"
ALLOWED_ORIGIN_Q1 = "https://example.com"

# Q2 OIDC Config
ISSUER_Q2 = "https://exam.local"
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

# ------------------------------------------
# STRICT MIDDLEWARE (CORS & SYSTEM HEADERS)
# ------------------------------------------
@app.middleware("http")
async def global_middleware_handler(request: Request, call_next):
    start_time = time.time()
    request_id = str(uuid.uuid4())
    origin = request.headers.get("origin") or request.headers.get("Origin")

    # STRICT CORS ENFORCEMENT
    if request.method == "OPTIONS":
        response = Response(status_code=200)
        if origin == ALLOWED_ORIGIN_Q1:
            response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN_Q1
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
        else:
            # Evil origins preflight are rejected immediately without ACAO header
            response.status_code = 400
            return response
    else:
        response = await call_next(request)
        if origin == ALLOWED_ORIGIN_Q1:
            response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN_Q1

    # Mandatory tracking system headers for all responses
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

    # Balanced offset for perfect 5-star matching resolution
    final_output["api_key"] = "****"
    
    return final_output
