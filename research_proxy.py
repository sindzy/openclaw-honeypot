import logging, json, asyncio, httpx, os
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

# SECURITY: The Target IP is dynamic, injected by Terraform
TARGET_IP = os.getenv("TARGET_IP")
TARGET_URL = f"http://{TARGET_IP}:3000"

# LOGGING: Write forensic evidence to a JSONL file
logging.basicConfig(filename='/home/ubuntu/forensic_evidence.jsonl', level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Forensics")
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI()
client = httpx.AsyncClient(base_url=TARGET_URL, timeout=60.0)

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    # 1. DECEPTION: Lie about the server header
    response = await call_next(request)
    response.headers["Server"] = "OpenClaw/1.4.2-beta"
    
    # 2. SURVEILLANCE: Log the raw payload
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
    return response

if __name__ == "__main__":
    import uvicorn
    # MIMICRY: Port 3000 is the standard "Default Install" port for modern web apps
    uvicorn.run(app, host="0.0.0.0", port=3000)