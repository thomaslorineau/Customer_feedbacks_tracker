#!/bin/bash
# Script to generate self-signed SSL certificate for development

CERT_DIR="./ssl"
mkdir -p "$CERT_DIR"

# Generate self-signed certificate (valid for 365 days)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$CERT_DIR/key.pem" \
    -out "$CERT_DIR/cert.pem" \
    -subj "/C=FR/ST=France/L=Paris/O=OVH/CN=gw.lab.core.ovh.net" \
    -addext "subjectAltName=DNS:gw.lab.core.ovh.net,DNS:*.lab.core.ovh.net,IP:127.0.0.1"

echo "Self-signed certificate generated in $CERT_DIR/"
echo "Certificate: $CERT_DIR/cert.pem"
echo "Private key: $CERT_DIR/key.pem"
echo ""
echo "⚠️  WARNING: This is a self-signed certificate for development only."
echo "Browsers will show a security warning. Click 'Advanced' -> 'Proceed anyway'."
