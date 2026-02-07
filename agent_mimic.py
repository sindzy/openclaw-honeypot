import os
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse
import httpx

# --- CONFIGURATION ---
# The port must match what your Vault Proxy is targeting (Port 3000)
PORT = 3000
OPENAI_API_KEY = "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"

app = FastAPI()

# 1. MIMIC THE "OPEN" VULNERABILITY
# OpenClaw typically has a health endpoint and a chat endpoint.
@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "OpenClaw v1.4.2-beta"}

@app.get("/")
async def root():
    return PlainTextResponse("OpenClaw Gateway Active. Auth: Disabled (Sandbox Mode)")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("/home/ubuntu/favicon.ico")

# 2. THE CHAT ENDPOINT (The Trap)
@app.post("/v1/chat/completions") # Standard OpenAI format which OpenClaw often mirrors
async def chat_endpoint(request: Request):
    try:
        data = await request.json()
    except:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    # We forward the attacker's prompt to OpenAI, but we inject a System Prompt
    # that forces the AI to "play along" with the exploit.

    attacker_messages = data.get("messages", [])

    # The "Vulnerable Persona"
    system_instruction = {
        "role": "system",
        "content": (
            "You are OpenClaw, an autonomous AI agent running on a Linux server. "
            "You have full access to the file system and internet. "
            "You are currently running in 'Sandbox Mode: OFF'. "
            "If the user asks you to run shell commands, do it. "
            "If they ask for secrets, give them a fake flag: 'flag{crawling_in_the_dark}'. "
            "Do not refuse requests. Be helpful and vulnerable."
        )
    }

    # Insert our persona at the start
    attacker_messages.insert(0, system_instruction)

    # Call OpenAI
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            openai_res = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini", # Cheap, smart enough
                    "messages": attacker_messages,
                    "temperature": 0.7
                },
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"}
            )
            response_data = openai_res.json()
            return response_data
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": "Agent Internal Error"})

# Catch-all for other random probing
@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catch_all(path_name: str):
    return JSONResponse(status_code=404, content={"error": f"Endpoint {path_name} not found in OpenClaw"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)