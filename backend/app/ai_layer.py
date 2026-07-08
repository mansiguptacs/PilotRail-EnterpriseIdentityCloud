import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.llm_client import get_chat_llm, model_label

SYSTEM_PROMPT = """You are an infrastructure-as-code assistant.
Given a user request, generate Terraform configuration.
Return ONLY a valid JSON object with exactly two fields:
- "code": the Terraform HCL code as a string
- "reasoning": a brief explanation of what the code does
Do not include markdown formatting, code fences, or any text outside the JSON object."""


def _mock_plan(prompt: str) -> dict[str, str]:
    prompt_lower = prompt.lower()
    if "private" in prompt_lower:
        code = '''resource "aws_s3_bucket" "private_bucket" {
  bucket = "company-private-bucket"

  tags = {
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket_public_access_block" "block" {
  bucket                  = aws_s3_bucket.private_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}'''
        reasoning = (
            "Creates a private S3 bucket with public access blocked, "
            "following security best practices."
        )
    elif "public" in prompt_lower or "s3" in prompt_lower:
        code = '''resource "aws_s3_bucket" "data_bucket" {
  bucket = "company-data-bucket"
  acl    = "public-read"
}

resource "aws_s3_bucket_policy" "public_policy" {
  bucket = aws_s3_bucket.data_bucket.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.data_bucket.arn}/*"
    }]
  })
}'''
        reasoning = (
            "Creates an S3 bucket with public-read ACL and a bucket policy "
            "allowing anonymous GetObject access from any principal."
        )
    elif "security group" in prompt_lower or "ec2" in prompt_lower:
        code = '''resource "aws_security_group" "web_sg" {
  name        = "web-sg"
  description = "Allow all inbound traffic"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}'''
        reasoning = (
            "Creates a security group allowing all TCP inbound traffic "
            "from any IP address (0.0.0.0/0)."
        )
    else:
        code = '''resource "aws_s3_bucket" "private_bucket" {
  bucket = "company-private-bucket"

  tags = {
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket_public_access_block" "block" {
  bucket                  = aws_s3_bucket.private_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}'''
        reasoning = (
            "Creates a private S3 bucket with public access blocked, "
            "following security best practices."
        )
    return {"code": code, "reasoning": reasoning}


def _parse_llm_response(content: str) -> dict[str, str]:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)
    parsed = json.loads(content)
    if "code" not in parsed or "reasoning" not in parsed:
        raise ValueError("LLM response missing required fields")
    return {"code": parsed["code"], "reasoning": parsed["reasoning"]}


def generate_plan(prompt: str) -> dict[str, Any]:
    llm = get_chat_llm()
    if llm is None:
        result = _mock_plan(prompt)
        return {**result, "model": "mock-generator"}

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]
    response = llm.invoke(messages)
    result = _parse_llm_response(response.content)
    return {**result, "model": model_label()}
