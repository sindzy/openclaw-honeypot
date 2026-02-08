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
    response.headers["Server"] = "OpenClaw/1.4.2-beta"
    return response

# 2. CATCH-ALL ROUTE: LOGGING & FORWARDING (The Missing Link)
@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"])
async def proxy_request(request: Request, path_name: str):
    # A. LOGGING
    try:
        body = await request.body()
        payload = body.decode('utf-8', errors='ignore')
    except:
        payload = "BINARY"
    
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "ingress",
        "src_ip": request.client.host,
        "method": request.method,
        "path": request.url.path,
        "payload_snippet": payload[:1000]
    }
    logger.info(json.dumps(log_entry))

    # B. FORWARDING
    try:
        # Reconstruct URL with query parameters
        url = request.url.path
        if request.url.query:
            url += "?" + request.url.query
            
        # Clean headers (avoid Host mismatches)
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
    uvicorn.run(app, host="0.0.0.0", port=3000)