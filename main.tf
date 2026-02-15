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

variable "management_ip" {
  description = "Management IP Address (Your Home IP)"
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
  bundle_id         = "nano_3_2"
  key_pair_name     = aws_lightsail_key_pair.lab_key.name
  
  # DISABLE IPv6 (Reduces attack surface)
  ip_address_type   = "ipv4"
  
  tags              = { Role = "Victim" }

  user_data = replace(templatefile("${path.module}/setup_bait.tftpl", {
    app_code   = file("${path.module}/agent_mimic.py")
    openai_key = var.openai_api_key
  }), "\r", "")
}

# --- HOST 2: THE PROXY (1GB) ---
resource "aws_lightsail_instance" "proxy" {
  name              = "vault-proxy"
  availability_zone = "ap-southeast-2a"
  blueprint_id      = "ubuntu_22_04"
  bundle_id         = "micro_3_2"
  key_pair_name     = aws_lightsail_key_pair.lab_key.name
  
  # DISABLE IPv6
  ip_address_type   = "ipv4"

  tags              = { Role = "Controller" }

  user_data = replace(templatefile("${path.module}/setup_proxy.tftpl", {
    app_code  = file("${path.module}/research_proxy.py")
    target_ip = aws_lightsail_instance.bait.private_ip_address
  }), "\r", "")
}

# --- FIREWALL RULES ---
resource "aws_lightsail_instance_public_ports" "bait_fw" {
  instance_name = aws_lightsail_instance.bait.name
  
  # FORCE WAIT: Ensure instance is ready before applying rules
  depends_on = [aws_lightsail_instance.bait]

  port_info {
    protocol  = "tcp"
    from_port = 22
    to_port   = 22
    cidrs     = ["${var.management_ip}/32"]
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
  
  # FORCE WAIT: Ensure instance is ready before applying rules
  depends_on = [aws_lightsail_instance.proxy]

  port_info {
    protocol  = "tcp"
    from_port = 22
    to_port   = 22
    cidrs     = ["${var.management_ip}/32"]
  }
  
  port_info {
    protocol  = "tcp"
    from_port = 3000
    to_port   = 3000
    cidrs     = ["0.0.0.0/0"]
  }

  port_info {
    protocol  = "tcp"
    from_port = 18789
    to_port   = 18789
    cidrs     = ["0.0.0.0/0"]
  }
}

output "proxy_public_ip" {
  value = aws_lightsail_instance.proxy.public_ip_address
}