import logging, json, asyncio, httpx, os
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

# CONFIGURATION
TARGET_IP = os.getenv("TARGET_IP")
TARGET_URL = f"http://{TARGET_IP}:3000"

# LOGGING
logging.basicConfig(filename='/home/ubuntu/forensic_evidence.jsonl', level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Forensics")
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI()
client = httpx.AsyncClient(base_url=TARGET_URL, timeout=60.0)

# 1. MIDDLEWARE: HEADER DECEPTION
@app.middleware("http")
async def spoof_server_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Server"] = "openclaw-gateway/1.4.2" 
    response.headers["Cache-Control"] = "no-cache"
    return response

# 2. CATCH-ALL ROUTE: LOGGING & FORWARDING
@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"])
async def proxy_request(request: Request, path_name: str):
    # A. LOGGING
    try:
        body = await request.body()
        payload = body.decode('utf-8', errors='ignore')
    except:
        payload = "BINARY"
    
    # Extract Headers for Fingerprinting (Shodan Detection)
    # We convert the immutable Headers object to a standard dict
    request_headers = dict(request.headers)

    log_entry = {
        # FIX: Use system timezone (Sydney)
        "timestamp": datetime.now().astimezone().isoformat(),
        "event_type": "ingress",
        "src_ip": request.client.host,
        "method": request.method,
        "path": request.url.path,
        "http_version": request.scope.get("http_version", "1.1"),
        "headers": request_headers, # <--- THE SHODAN FINGERPRINT
        "payload_snippet": payload[:2000] # Increased capture size
    }
    logger.info(json.dumps(log_entry))

    # B. FORWARDING
    try:
        # Reconstruct URL with query parameters
        url = request.url.path
        if request.url.query:
            url += "?" + request.url.query
            
        # Clean headers to avoid Host mismatches upstream
        proxy_headers = dict(request.headers)
        proxy_headers.pop("host", None)
        proxy_headers.pop("content-length", None) 

        # Build and Send
        proxy_req = client.build_request(
            request.method,
            url,
            content=body,
            headers=proxy_headers
        )
        r = await client.send(proxy_req)
        
        return Response(content=r.content, status_code=r.status_code, headers=r.headers)

    except httpx.RequestError as exc:
        return JSONResponse(status_code=502, content={"error": f"Upstream Error: {str(exc)}"})
        
if __name__ == "__main__":
    import uvicorn
    # server_header=False ensures we don't leak "uvicorn" alongside "OpenClaw"
    uvicorn.run(app, host="0.0.0.0", port=3000, server_header=False)