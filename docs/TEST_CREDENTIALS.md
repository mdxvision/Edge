# Test Credentials

## Application Login

| Field | Value |
|-------|-------|
| **Email** | `test@edgebet.com` |
| **Username** | `testuser` |
| **Password** | `TestPass123!` |

You can use either email or username to log in.

## How to Create Test User

If the test user doesn't exist, run:

```bash
cd /Users/rafaelrodriguez/GitHub/Edge
./venv/bin/python scripts/seed_test_user.py
```

## URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5001 |
| Backend API | http://localhost:8080 |

## Starting the App

```bash
# Terminal 1 - Backend
cd /Users/rafaelrodriguez/GitHub/Edge
./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Terminal 2 - Frontend
cd /Users/rafaelrodriguez/GitHub/Edge/client
npm run dev
```
