import logging, json, asyncio, httpx, os, sys
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

# CONFIGURATION
TARGET_IP = os.getenv("TARGET_IP")
TARGET_URL = f"http://{TARGET_IP}:3000"
LISTEN_PORT = int(os.getenv("LISTEN_PORT", "3000"))
LOG_FILE = os.getenv("LOG_FILE", "/home/ubuntu/forensics.jsonl")

# LOGGING
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(message)s')
logger = logging.getLogger(f"Forensics-{LISTEN_PORT}")
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI()
client = httpx.AsyncClient(base_url=TARGET_URL, timeout=60.0)

# 1. MIDDLEWARE: HEADER DECEPTION
@app.middleware("http")
async def spoof_server_header(request: Request, call_next):
    response = await call_next(request)
    # The "Control Panel" usually reports a slightly different header. 
    # We can adapt based on port if we want, but "openclaw-gateway" is safe for both.
    response.headers["Server"] = "openclaw-gateway/1.4.2" 
    response.headers["Cache-Control"] = "no-cache"
    return response

# 2. CATCH-ALL ROUTE
@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"])
async def proxy_request(request: Request, path_name: str):
    try:
        body = await request.body()
        payload = body.decode('utf-8', errors='ignore')
    except:
        payload = "BINARY"
    
    request_headers = dict(request.headers)

    log_entry = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "event_type": "ingress",
        "listen_port": LISTEN_PORT,  # <--- CRITICAL: Logs which trap triggered
        "src_ip": request.client.host,
        "method": request.method,
        "path": request.url.path,
        "headers": request_headers,
        "payload_snippet": payload[:2000]
    }
    logger.info(json.dumps(log_entry))

    # FORWARDING
    try:
        url = request.url.path
        if request.url.query:
            url += "?" + request.url.query
            
        proxy_headers = dict(request.headers)
        proxy_headers.pop("host", None)
        proxy_headers.pop("content-length", None) 

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
    # Listen on the port defined by Env Var
    uvicorn.run(app, host="0.0.0.0", port=LISTEN_PORT, server_header=False)