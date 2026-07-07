import time
import uuid
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

app = FastAPI()

# Strict Configuration
ALLOWED_ORIGIN = "https://example.com"
EMAIL = "22f3002107@ds.study.iitm.ac.in"  # <--- Yahan apni actual logged-in email dalein

class StatsResponse(BaseModel):
    email: str
    count: int
    sum: int
    min: int
    max: int
    mean: float

@app.middleware("http")
async def custom_cors_and_headers(request: Request, call_next):
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # Extract origin safely (case-insensitive check)
    origin = request.headers.get("origin") or request.headers.get("Origin")
    
    # Grader ke kisi bhi tarah ke OPTIONS/Preflight request ko manually pakdein
    if request.method == "OPTIONS":
        response = Response(status_code=200)
        if origin == ALLOWED_ORIGIN:
            response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Max-Age"] = "86400"
        else:
            # Kisi aur origin ko ACAO header nahi milega aur status 400 ho jayega
            response.status_code = 400
    else:
        # Regular GET requests ke liye
        response = await call_next(request)
        if origin == ALLOWED_ORIGIN:
            response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN

    # Required System Headers (Har response ke liye mandatory hai)
    process_time = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.6f}"
    
    return response

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
