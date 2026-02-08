terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-southeast-2"
}

# --- SECURE VARIABLES ---
variable "openai_api_key" {
  description = "OpenAI API Key for the Bait"
  type        = string
  sensitive   = true 
}

# --- SSH KEY ---
resource "aws_lightsail_key_pair" "lab_key" {
  name       = "honeypot-key-v3"
  public_key = file(".ssh/honeypot_key.pub")
}

# --- HOST 1: THE BAIT (512MB) ---
resource "aws_lightsail_instance" "bait" {
  name              = "bait-victim"
  availability_zone = "ap-southeast-2a"
  blueprint_id      = "ubuntu_22_04"
  bundle_id         = "nano_3_0"
  key_pair_name     = aws_lightsail_key_pair.lab_key.name
  tags              = { Role = "Victim" }

  # Inject Code + Secret Key
  user_data = templatefile("${path.module}/setup_bait.tftpl", {
    app_code   = file("${path.module}/agent_mimic.py")
    openai_key = var.openai_api_key
  })
}

# --- HOST 2: THE PROXY (1GB) ---
resource "aws_lightsail_instance" "proxy" {
  name              = "vault-proxy"
  availability_zone = "ap-southeast-2a"
  blueprint_id      = "ubuntu_22_04"
  bundle_id         = "micro_3_0" # 1GB RAM (Reserved for Manual Elastic Install)
  key_pair_name     = aws_lightsail_key_pair.lab_key.name
  tags              = { Role = "Controller" }

  # Inject Code + Dynamic Bait IP
  user_data = templatefile("${path.module}/setup_proxy.tftpl", {
    app_code  = file("${path.module}/research_proxy.py")
    target_ip = aws_lightsail_instance.bait.private_ip_address
  })
}

# --- FIREWALL RULES ---
resource "aws_lightsail_instance_public_ports" "bait_fw" {
  instance_name = aws_lightsail_instance.bait.name
  
  port_info {
    protocol  = "tcp"
    from_port = 22
    to_port   = 22
    cidrs     = ["0.0.0.0/0"]
  }
  
  port_info {
    protocol  = "tcp"
    from_port = 3000
    to_port   = 3000
    cidrs     = ["${aws_lightsail_instance.proxy.private_ip_address}/32"]
  }
}

resource "aws_lightsail_instance_public_ports" "proxy_fw" {
  instance_name = aws_lightsail_instance.proxy.name
  
  port_info {
    protocol  = "tcp"
    from_port = 22
    to_port   = 22
    cidrs     = ["0.0.0.0/0"]
  }
  
  # MIMICRY: Port 3000 (Standard Web UI)
  port_info {
    protocol  = "tcp"
    from_port = 3000
    to_port   = 3000
    cidrs     = ["0.0.0.0/0"]
  }
}

output "proxy_public_ip" {
  value = aws_lightsail_instance.proxy.public_ip_address
}