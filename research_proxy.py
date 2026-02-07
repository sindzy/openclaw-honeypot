import logging
import json
import asyncio
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import httpx

# --- CONFIGURATION ---
TARGET_IP = "172.26.0.208"  # The Private IP of your Bait instance
TARGET_URL = f"http://{TARGET_IP}:3000"

# --- LOGGING SETUP ---
# 1. Setup Forensic Logging (JSON format for Elastic)
logging.basicConfig(
    filename='forensic_evidence.jsonl',
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger("Forensics")

# 2. Silence the noisy "HTTP Request: POST..." logs from libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# --- APP INITIALIZATION ---
app = FastAPI()  # <--- THIS MUST COME BEFORE MIDDLEWARE
client = httpx.AsyncClient(base_url=TARGET_URL, timeout=60.0)

# --- MIDDLEWARE 1: HEADER SPOOFING (Deception) ---
@app.middleware("http")
async def spoof_server_header(request: Request, call_next):
    response = await call_next(request)
    # The Lie: Claim to be the real agent, not Python/Uvicorn
    response.headers["Server"] = "OpenClaw/1.4.2-beta"
    response.headers["X-Powered-By"] = "OpenClaw Core"
    return response

# --- MIDDLEWARE 2: FORENSIC LOGGING (Surveillance) ---
@app.middleware("http")
async def forensic_logger(request: Request, call_next):
    # 1. CPU Protection (Anti-DDoS)
    # Slight delay to let the t3.nano CPU breathe during floods
    await asyncio.sleep(0.1)

    # 2. Capture the Attack Payload
    try:
        body = await request.body()
        body_str = body.decode('utf-8', errors='ignore')
    except:
        body_str = "BINARY_PAYLOAD"

    entry_log = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "ingress",
        "src_ip": request.client.host,
        "method": request.method,
        "path": request.url.path,
        "user_agent": request.headers.get("user-agent"),
        "payload_size": len(body),
        "payload_snippet": body_str[:1000]
    }
    logger.info(json.dumps(entry_log))

    # 3. Forward to Victim (The Bait)
    try:
        proxy_req = client.build_request(
            request.method,
            request.url.path,
            content=body,
            headers=request.headers.raw
        )
        r = await client.send(proxy_req)

        # 4. Capture the Response
        response_snippet = r.text[:1000]

        resp_log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "egress",
            "status": r.status_code,
            "agent_reply_snippet": response_snippet
        }
        logger.info(json.dumps(resp_log))

        return Response(content=r.content, status_code=r.status_code, headers=r.headers)

    except httpx.ConnectError:
        error_log = {
             "timestamp": datetime.now(timezone.utc).isoformat(),
             "event_type": "error",
             "msg": "BAIT_HOST_UNREACHABLE"
        }
        logger.critical(json.dumps(error_log))
        return JSONResponse(status_code=502, content={"error": "Upstream Agent Offline"})