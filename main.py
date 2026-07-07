import time
import uuid
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

app = FastAPI()

# Configuration variables
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
async def add_custom_headers_and_cors(request: Request, call_next):
    start_time = time.time()
    
    # Unique Request ID generate karein
    request_id = str(uuid.uuid4())
    
    # Incoming request se Origin header extract karein
    origin = request.headers.get("Origin")
    
    # Preflight OPTIONS requests ko manually handle karein strict CORS control ke liye
    if request.method == "OPTIONS":
        response = Response()
        if origin == ALLOWED_ORIGIN:
            response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Request-ID"
            response.status_code = 200
        else:
            # Galat origin hone par preflight ko reject karein bina ACAO header ke
            response.status_code = 400
    else:
        # Normal GET request ko aage badhayein
        response = await call_next(request)
        if origin == ALLOWED_ORIGIN:
            response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN

    # Execution time calculate karein
    process_time = time.time() - start_time
    
    # Har ek response mein required middleware headers inject karein
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.6f}"
    
    return response

@app.get("/stats", response_model=StatsResponse)
async def get_stats(values: str = Query(..., description="Comma-separated list of integers")):
    try:
        # Comma-separated string ko integers ki list mein convert karein
        int_values = [int(x.strip()) for x in values.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid input. Please provide comma-separated integers.")
    
    if not int_values:
        raise HTTPException(status_code=400, detail="Values list cannot be empty.")
    
    # Live statistics calculate karein (grader ke random inputs ke liye)
    count = len(int_values)
    total_sum = sum(int_values)
    min_val = min(int_values)
    max_val = max(int_values)
    mean_val = round(total_sum / count, 4)  # ±0.01 ki margin ke andar rahega
    
    return {
        "email": EMAIL,
        "count": count,
        "sum": total_sum,
        "min": min_val,
        "max": max_val,
        "mean": mean_val
    }
