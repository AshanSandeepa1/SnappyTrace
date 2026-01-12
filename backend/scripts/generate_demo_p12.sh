#!/usr/bin/env bash
set -euo pipefail

mkdir -p "$(dirname "$0")/../app/certs"
OUT_DIR="$(dirname "$0")/../app/certs"
KEY="$OUT_DIR/demo.key"
CRT="$OUT_DIR/demo.crt"
P12="$OUT_DIR/demo.p12"
PASS="demo-password"

echo "Generating demo RSA key and self-signed certificate..."
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out "$KEY"
openssl req -new -x509 -key "$KEY" -out "$CRT" -days 365 -subj "/CN=SnappyTrace Demo/O=SnappyTrace"

echo "Bundling into PKCS#12: $P12"
openssl pkcs12 -export -out "$P12" -inkey "$KEY" -in "$CRT" -passout pass:$PASS

echo "Generated demo PKCS#12: $P12 (password: $PASS)"
openssl x509 -in "$CRT" -noout -fingerprint -sha256
