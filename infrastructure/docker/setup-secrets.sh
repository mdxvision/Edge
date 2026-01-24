#!/bin/bash
# Setup Docker secrets for production deployment
# Run this script once before first deployment

set -e

SECRETS_DIR="$(dirname "$0")/secrets"

echo "Setting up Docker secrets in $SECRETS_DIR"

# Create secrets directory
mkdir -p "$SECRETS_DIR"

# Generate secrets if they don't exist
if [ ! -f "$SECRETS_DIR/postgres_user.txt" ]; then
    echo "edge" > "$SECRETS_DIR/postgres_user.txt"
    echo "Created postgres_user.txt"
fi

if [ ! -f "$SECRETS_DIR/postgres_password.txt" ]; then
    openssl rand -base64 32 > "$SECRETS_DIR/postgres_password.txt"
    echo "Created postgres_password.txt (random)"
fi

if [ ! -f "$SECRETS_DIR/session_secret.txt" ]; then
    openssl rand -base64 48 > "$SECRETS_DIR/session_secret.txt"
    echo "Created session_secret.txt (random)"
fi

if [ ! -f "$SECRETS_DIR/odds_api_key.txt" ]; then
    echo "YOUR_ODDS_API_KEY_HERE" > "$SECRETS_DIR/odds_api_key.txt"
    echo "Created odds_api_key.txt (PLACEHOLDER - update with real key)"
fi

if [ ! -f "$SECRETS_DIR/stripe_secret.txt" ]; then
    echo "sk_test_xxx" > "$SECRETS_DIR/stripe_secret.txt"
    echo "Created stripe_secret.txt (PLACEHOLDER - update with real key)"
fi

# Set proper permissions
chmod 600 "$SECRETS_DIR"/*.txt
chmod 700 "$SECRETS_DIR"

echo ""
echo "Secrets created in $SECRETS_DIR"
echo "IMPORTANT: Update placeholder values in:"
echo "  - odds_api_key.txt"
echo "  - stripe_secret.txt"
echo ""
echo "To start production: docker-compose up -d"
echo "To start development: docker-compose -f docker-compose.yml -f docker-compose.dev.yml up"
