terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# --- MISSING KEY PAIR RESOURCE ---
resource "aws_lightsail_key_pair" "lab_key" {
  name       = "honeypot-key"
  public_key = file(".ssh/honeypot_key.pub")
}

# 1. CONFIGURE PROVIDER
provider "aws" {
  region = "ap-southeast-2" # CHANGE THIS if your SSH key is in another region
}

# Host A: The Vault
resource "aws_lightsail_instance" "vault" {
  name              = "vault-proxy"
  availability_zone = "ap-southeast-2a" # Ensure this matches your region
  blueprint_id      = "ubuntu_22_04"
  bundle_id         = "nano_3_2"      # <--- SYDNEY SPECIFIC ID
  key_pair_name     = aws_lightsail_key_pair.lab_key.name

  tags = {
    Role = "Controller"
  }
}

# Open ports on The Vault (Public Internet Access)
resource "aws_lightsail_instance_public_ports" "vault_firewall" {
  instance_name = aws_lightsail_instance.vault.name

  # SSH (Admin access)
  port_info {
    protocol  = "tcp"
    from_port = 22
    to_port   = 22
    cidrs     = ["0.0.0.0/0"] # Suggestion: Restrict this to your Home IP manually later
  }

  # Proxy Port (Where attackers hit)
  port_info {
    protocol  = "tcp"
    from_port = 8080
    to_port   = 8080
    cidrs     = ["0.0.0.0/0"]
  }
}

# Host B: The Bait
resource "aws_lightsail_instance" "bait" {
  name              = "bait-victim"
  availability_zone = "ap-southeast-2a"
  blueprint_id      = "ubuntu_22_04"
  bundle_id         = "micro_3_2"     # <--- SYDNEY SPECIFIC ID
  key_pair_name     = aws_lightsail_key_pair.lab_key.name

  tags = {
    Role = "Victim"
  }
}

# Firewall for The Bait (RESTRICTED)
# Only allows SSH (for you) and Port 3000 (from The Vault only)
resource "aws_lightsail_instance_public_ports" "bait_firewall" {
  instance_name = aws_lightsail_instance.bait.name

  # SSH (Admin access for setup)
  port_info {
    protocol  = "tcp"
    from_port = 22
    to_port   = 22
    cidrs     = ["0.0.0.0/0"]
  }

  # Application Port - ONLY Accessible from The Vault's Private IP
  port_info {
    protocol  = "tcp"
    from_port = 3000
    to_port   = 3000
    cidrs     = ["${aws_lightsail_instance.vault.private_ip_address}/32"]
  }
}

# --- OUTPUTS ---
output "vault_public_ip" {
  value = aws_lightsail_instance.vault.public_ip_address
  description = "SSH into Vault: ssh -i ~/.ssh/honeypot-key.pem ubuntu@<IP>"
}

output "bait_private_ip" {
  value = aws_lightsail_instance.bait.private_ip_address
  description = "Use this IP in your Python Proxy script as TARGET_IP"
}

output "bait_public_ip" {
  value = aws_lightsail_instance.bait.public_ip_address
  description = "SSH into Bait: ssh -i ~/.ssh/honeypot-key.pem ubuntu@<IP>"
}