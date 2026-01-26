#!/bin/bash
# Run all tests before pushing
# Usage: ./scripts/run-tests.sh [--skip-e2e]

set -e
cd "$(dirname "$0")/.."

echo "🧪 Running test suite..."

# Backend tests
echo ""
echo "1️⃣  Backend unit tests..."
source venv/bin/activate 2>/dev/null || true
python -m pytest tests/ -v --tb=short
echo "✅ Backend tests passed"

# Frontend build
echo ""
echo "2️⃣  Frontend TypeScript build..."
cd client
npm run build
echo "✅ Frontend build passed"

# E2E tests (optional)
if [ "$1" != "--skip-e2e" ]; then
    echo ""
    echo "3️⃣  Cypress E2E tests..."
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        CYPRESS_BASE_URL=http://localhost:5173 npx cypress run --browser chrome
        echo "✅ E2E tests passed"
    else
        echo "⚠️  Backend not running. Start servers first:"
        echo "   ./start_app.sh"
        echo "   Then re-run: ./scripts/run-tests.sh"
        exit 1
    fi
else
    echo ""
    echo "⏭️  Skipping E2E tests (--skip-e2e)"
fi

echo ""
echo "✅ All tests passed! Safe to push."
