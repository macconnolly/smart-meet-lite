#!/bin/bash

# Script to set up Zscaler certificate for pip and system

echo "Setting up Zscaler certificate..."

# Get absolute path to certificate
CERT_PATH="$(pwd)/zscaler.crt"

# 1. Configure pip to use the certificate
echo "Configuring pip..."
venv/bin/python -m pip config set global.cert "$CERT_PATH"

# 2. Set environment variables for current session
export REQUESTS_CA_BUNDLE="$CERT_PATH"
export SSL_CERT_FILE="$CERT_PATH"
export CURL_CA_BUNDLE="$CERT_PATH"
export NODE_EXTRA_CA_CERTS="$CERT_PATH"

# 3. Create a combined certificate bundle for Python requests
echo "Creating combined certificate bundle..."
cat /etc/ssl/certs/ca-certificates.crt "$CERT_PATH" > combined-ca-bundle.crt 2>/dev/null || true

# 4. Instructions for system-level setup (requires sudo)
echo ""
echo "Certificate configuration complete for current session."
echo ""
echo "For system-wide configuration (requires sudo), run:"
echo "  sudo cp $CERT_PATH /usr/local/share/ca-certificates/zscaler.crt"
echo "  sudo update-ca-certificates"
echo ""
echo "To make environment variables permanent, add these to your ~/.bashrc:"
echo "  export REQUESTS_CA_BUNDLE='$CERT_PATH'"
echo "  export SSL_CERT_FILE='$CERT_PATH'"
echo "  export CURL_CA_BUNDLE='$CERT_PATH'"
echo "  export NODE_EXTRA_CA_CERTS='$CERT_PATH'"
echo ""

# Test pip connectivity
echo "Testing pip connectivity..."
venv/bin/python -m pip list > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Pip connectivity test passed"
else
    echo "✗ Pip connectivity test failed"
fi