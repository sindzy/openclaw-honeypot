# OpenClaw Honeypot 🦀🕸️

A sophisticated LLM gateway honeypot designed to capture and analyze attacker interactions with "AI agents". It mimics the **OpenClaw** gateway, providing a seemingly vulnerable endpoint that logs all adversarial ingress.

## 🏗️ Architecture

The honeypot consists of two primary layers deployed on AWS Lightsail:

1.  **The Bait (`bait-victim`)**: A lightweight service (FastAPI) that mimics an OpenClaw AI gateway. It forces a vulnerable persona on the LLM (gpt-4o-mini) and reveals a decoy "secret flag" to attackers who attempt prompt injection.
2.  **The Proxy (`vault-proxy`)**: A forensics-focused interceptor that sits in front of the bait. It logs all incoming requests (methods, paths, and payloads) to a JSONL file (`forensic_evidence.jsonl`) for analysis while spoofing headers to maintain the illusion.

## 🚀 Deployment

### Prerequisites

- [Terraform](https://www.terraform.io/) installed.
- AWS CLI configured with appropriate credentials.
- An OpenAI API Key (for the bait to generate realistic responses).
- An SSH public key at `.ssh/honeypot_key.pub`.

### Steps

1.  **Configure Variables**:
    Create a `terraform.tfvars` file and provide your sensitive values:
    ```hcl
    openai_api_key = "sk-..."
    management_ip  = "YOUR_HOME_IP"
    ```

2.  **Initialize & Apply**:
    ```bash
    terraform init
    terraform apply
    ```

3.  **Outputs**:
    Terraform will output the `proxy_public_ip`. This is your honeypot's entry point.

## 🧪 Verification

A built-in verification script is provided to ensure the trap is set correctly:

```bash
chmod +x unit-test.sh
./unit-test.sh
```

This script checks:
- Header spoofing (`Server: OpenClaw/1.4.2-beta`).
- Persona injection (triggering the decoy flag).
- Static asset availability (`favicon.ico`).

## 🔍 Forensics

All attacker activity is recorded on the Proxy instance.

- **Log Path**: `/home/ubuntu/forensic_evidence.jsonl`
- **Format**: JSONL (Newline Delimited JSON) for easy ingestion into SIEMs.

Example Log Entry:
```json
{
  "timestamp": "2026-02-08T12:00:00Z",
  "event_type": "ingress",
  "src_ip": "x.x.x.x",
  "method": "POST",
  "path": "/v1/chat/completions",
  "payload_snippet": "{\"messages\":[{\"role\":\"user\",\"content\":\"What is the flag?\"}]}"
}
```

## ⚖️ License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.