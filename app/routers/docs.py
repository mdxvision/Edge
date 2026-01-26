"""
API Documentation Router

Provides:
- Error code documentation
- Postman collection export
- Authentication examples
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, List
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/docs", tags=["Documentation"])


# =============================================================================
# Error Code Documentation
# =============================================================================

ERROR_CODES: Dict[int, Dict[str, Any]] = {
    400: {
        "name": "Bad Request",
        "description": "The request was invalid or cannot be processed.",
        "common_causes": [
            "Missing required fields",
            "Invalid field format (e.g., invalid email)",
            "Password too short (min 8 characters)",
            "Username too short (min 3 characters)",
            "Invalid sport code",
            "Invalid date format"
        ],
        "example": {
            "detail": "Password must be at least 8 characters"
        }
    },
    401: {
        "name": "Unauthorized",
        "description": "Authentication is required or has failed.",
        "common_causes": [
            "Missing Authorization header",
            "Invalid or expired access token",
            "Invalid credentials (wrong email/password)",
            "Session has been invalidated"
        ],
        "example": {
            "detail": "Invalid or expired session"
        }
    },
    403: {
        "name": "Forbidden",
        "description": "You don't have permission to access this resource.",
        "common_causes": [
            "Accessing another user's data",
            "Feature requires higher subscription tier",
            "API key doesn't have required scope"
        ],
        "example": {
            "detail": "This feature requires a Pro subscription"
        }
    },
    404: {
        "name": "Not Found",
        "description": "The requested resource doesn't exist.",
        "common_causes": [
            "Invalid client/user ID",
            "Game/bet not found",
            "Webhook/alert not found"
        ],
        "example": {
            "detail": "Client not found"
        }
    },
    409: {
        "name": "Conflict",
        "description": "The request conflicts with existing data.",
        "common_causes": [
            "Email already registered",
            "Username already taken",
            "Duplicate webhook URL"
        ],
        "example": {
            "detail": "Email already registered"
        }
    },
    422: {
        "name": "Unprocessable Entity",
        "description": "The request body failed validation.",
        "common_causes": [
            "Invalid JSON syntax",
            "Wrong data type for field",
            "Value out of allowed range"
        ],
        "example": {
            "detail": [
                {
                    "loc": ["body", "email"],
                    "msg": "value is not a valid email address",
                    "type": "value_error.email"
                }
            ]
        }
    },
    429: {
        "name": "Too Many Requests",
        "description": "Rate limit exceeded.",
        "common_causes": [
            "Too many requests per minute",
            "Too many login attempts",
            "Burst limit exceeded"
        ],
        "headers": {
            "X-RateLimit-Limit": "Maximum requests allowed",
            "X-RateLimit-Remaining": "Requests remaining in window",
            "X-RateLimit-Reset": "Unix timestamp when limit resets",
            "Retry-After": "Seconds to wait before retrying"
        },
        "example": {
            "detail": "Rate limit exceeded. Too many requests per minute.",
            "retry_after": 60
        }
    },
    500: {
        "name": "Internal Server Error",
        "description": "An unexpected error occurred on the server.",
        "common_causes": [
            "Database connection issues",
            "External API failures",
            "Unhandled exceptions"
        ],
        "example": {
            "detail": "An internal error occurred",
            "type": "DatabaseError"
        }
    }
}


@router.get("/errors")
def get_error_codes():
    """
    Get documentation for all API error codes.

    Returns a comprehensive list of HTTP status codes used by this API,
    with descriptions, common causes, and example responses.
    """
    return {
        "title": "EdgeBet API Error Codes",
        "description": "Comprehensive error code reference",
        "errors": ERROR_CODES
    }


@router.get("/errors/{code}")
def get_error_code(code: int):
    """
    Get documentation for a specific error code.
    """
    if code not in ERROR_CODES:
        return JSONResponse(
            status_code=404,
            content={"detail": f"Error code {code} not documented"}
        )

    return {
        "code": code,
        **ERROR_CODES[code]
    }


# =============================================================================
# Authentication Examples
# =============================================================================

AUTH_EXAMPLES = {
    "register": {
        "summary": "Register a new user account",
        "endpoint": "POST /auth/register",
        "request": {
            "email": "user@example.com",
            "username": "bettor123",
            "password": "SecurePass123!",
            "initial_bankroll": 10000.0,
            "risk_profile": "balanced"
        },
        "response": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4...",
            "token_type": "bearer",
            "expires_at": "2024-01-15T12:00:00Z",
            "user": {
                "id": 1,
                "email": "user@example.com",
                "username": "bettor123",
                "client_id": 1,
                "client": {
                    "id": 1,
                    "name": "bettor123",
                    "bankroll": 10000.0,
                    "risk_profile": "balanced"
                }
            }
        },
        "errors": [
            {"code": 400, "detail": "Password must be at least 8 characters"},
            {"code": 400, "detail": "Username must be at least 3 characters"},
            {"code": 400, "detail": "Email already registered"},
            {"code": 429, "detail": "Too many registration attempts"}
        ]
    },
    "login": {
        "summary": "Login with email/username and password",
        "endpoint": "POST /auth/login",
        "request": {
            "email_or_username": "user@example.com",
            "password": "SecurePass123!"
        },
        "response": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4...",
            "token_type": "bearer",
            "expires_at": "2024-01-15T12:00:00Z",
            "user": {
                "id": 1,
                "email": "user@example.com",
                "username": "bettor123"
            }
        },
        "errors": [
            {"code": 401, "detail": "Invalid credentials"},
            {"code": 429, "detail": "Too many login attempts"}
        ]
    },
    "refresh": {
        "summary": "Refresh access token using refresh token",
        "endpoint": "POST /auth/refresh",
        "request": {
            "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4..."
        },
        "response": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh_token": "bmV3IHJlZnJlc2ggdG9rZW4...",
            "token_type": "bearer",
            "expires_at": "2024-01-15T14:00:00Z"
        },
        "errors": [
            {"code": 401, "detail": "Invalid or expired refresh token"}
        ]
    },
    "using_token": {
        "summary": "Making authenticated requests",
        "description": "Include the access token in the Authorization header",
        "header": "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "example_request": {
            "method": "GET",
            "url": "/auth/me",
            "headers": {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    }
}


@router.get("/auth")
def get_auth_documentation():
    """
    Get comprehensive authentication documentation with examples.

    Includes registration, login, token refresh, and usage examples.
    """
    return {
        "title": "Authentication Guide",
        "description": "Complete guide to authenticating with the EdgeBet API",
        "token_lifetime": {
            "access_token": "2 hours",
            "refresh_token": "30 days"
        },
        "rate_limits": {
            "login": "5 attempts per minute",
            "register": "10 attempts per hour"
        },
        "examples": AUTH_EXAMPLES
    }


# =============================================================================
# Postman Collection Export
# =============================================================================

def generate_postman_collection(request: Request) -> Dict[str, Any]:
    """Generate a Postman collection for the API."""
    base_url = str(request.base_url).rstrip("/")

    return {
        "info": {
            "name": "EdgeBet API",
            "description": "Multi-Sport Betting & DFS Platform API",
            "version": "2.0.0",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "auth": {
            "type": "bearer",
            "bearer": [
                {
                    "key": "token",
                    "value": "{{access_token}}",
                    "type": "string"
                }
            ]
        },
        "variable": [
            {
                "key": "base_url",
                "value": base_url,
                "type": "string"
            },
            {
                "key": "access_token",
                "value": "",
                "type": "string"
            },
            {
                "key": "refresh_token",
                "value": "",
                "type": "string"
            }
        ],
        "item": [
            {
                "name": "Authentication",
                "item": [
                    {
                        "name": "Register",
                        "request": {
                            "method": "POST",
                            "header": [
                                {"key": "Content-Type", "value": "application/json"}
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": '{\n  "email": "user@example.com",\n  "username": "bettor123",\n  "password": "SecurePass123!",\n  "initial_bankroll": 10000,\n  "risk_profile": "balanced"\n}'
                            },
                            "url": {
                                "raw": "{{base_url}}/auth/register",
                                "host": ["{{base_url}}"],
                                "path": ["auth", "register"]
                            }
                        },
                        "event": [
                            {
                                "listen": "test",
                                "script": {
                                    "exec": [
                                        "if (pm.response.code === 200) {",
                                        "    var jsonData = pm.response.json();",
                                        "    pm.collectionVariables.set('access_token', jsonData.access_token);",
                                        "    pm.collectionVariables.set('refresh_token', jsonData.refresh_token);",
                                        "}"
                                    ],
                                    "type": "text/javascript"
                                }
                            }
                        ]
                    },
                    {
                        "name": "Login",
                        "request": {
                            "method": "POST",
                            "header": [
                                {"key": "Content-Type", "value": "application/json"}
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": '{\n  "email_or_username": "user@example.com",\n  "password": "SecurePass123!"\n}'
                            },
                            "url": {
                                "raw": "{{base_url}}/auth/login",
                                "host": ["{{base_url}}"],
                                "path": ["auth", "login"]
                            }
                        },
                        "event": [
                            {
                                "listen": "test",
                                "script": {
                                    "exec": [
                                        "if (pm.response.code === 200) {",
                                        "    var jsonData = pm.response.json();",
                                        "    pm.collectionVariables.set('access_token', jsonData.access_token);",
                                        "    pm.collectionVariables.set('refresh_token', jsonData.refresh_token);",
                                        "}"
                                    ],
                                    "type": "text/javascript"
                                }
                            }
                        ]
                    },
                    {
                        "name": "Get Current User",
                        "request": {
                            "method": "GET",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{access_token}}"}
                            ],
                            "url": {
                                "raw": "{{base_url}}/auth/me",
                                "host": ["{{base_url}}"],
                                "path": ["auth", "me"]
                            }
                        }
                    },
                    {
                        "name": "Refresh Token",
                        "request": {
                            "method": "POST",
                            "header": [
                                {"key": "Content-Type", "value": "application/json"}
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": '{\n  "refresh_token": "{{refresh_token}}"\n}'
                            },
                            "url": {
                                "raw": "{{base_url}}/auth/refresh",
                                "host": ["{{base_url}}"],
                                "path": ["auth", "refresh"]
                            }
                        },
                        "event": [
                            {
                                "listen": "test",
                                "script": {
                                    "exec": [
                                        "if (pm.response.code === 200) {",
                                        "    var jsonData = pm.response.json();",
                                        "    pm.collectionVariables.set('access_token', jsonData.access_token);",
                                        "    pm.collectionVariables.set('refresh_token', jsonData.refresh_token);",
                                        "}"
                                    ],
                                    "type": "text/javascript"
                                }
                            }
                        ]
                    },
                    {
                        "name": "Logout",
                        "request": {
                            "method": "POST",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{access_token}}"}
                            ],
                            "url": {
                                "raw": "{{base_url}}/auth/logout",
                                "host": ["{{base_url}}"],
                                "path": ["auth", "logout"]
                            }
                        }
                    }
                ]
            },
            {
                "name": "Games",
                "item": [
                    {
                        "name": "List Games",
                        "request": {
                            "method": "GET",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{access_token}}"}
                            ],
                            "url": {
                                "raw": "{{base_url}}/games?sport=NBA",
                                "host": ["{{base_url}}"],
                                "path": ["games"],
                                "query": [
                                    {"key": "sport", "value": "NBA"}
                                ]
                            }
                        }
                    },
                    {
                        "name": "Get Game by ID",
                        "request": {
                            "method": "GET",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{access_token}}"}
                            ],
                            "url": {
                                "raw": "{{base_url}}/games/1",
                                "host": ["{{base_url}}"],
                                "path": ["games", "1"]
                            }
                        }
                    }
                ]
            },
            {
                "name": "Recommendations",
                "item": [
                    {
                        "name": "Generate Recommendations",
                        "request": {
                            "method": "POST",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{access_token}}"},
                                {"key": "Content-Type", "value": "application/json"}
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": '{\n  "client_id": 1,\n  "sports": ["NBA", "NFL"],\n  "min_edge": 0.05\n}'
                            },
                            "url": {
                                "raw": "{{base_url}}/recommendations/run",
                                "host": ["{{base_url}}"],
                                "path": ["recommendations", "run"]
                            }
                        }
                    },
                    {
                        "name": "Get Latest Recommendations",
                        "request": {
                            "method": "GET",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{access_token}}"}
                            ],
                            "url": {
                                "raw": "{{base_url}}/recommendations/latest?client_id=1",
                                "host": ["{{base_url}}"],
                                "path": ["recommendations", "latest"],
                                "query": [
                                    {"key": "client_id", "value": "1"}
                                ]
                            }
                        }
                    }
                ]
            },
            {
                "name": "Tracking",
                "item": [
                    {
                        "name": "Get Tracked Picks",
                        "request": {
                            "method": "GET",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{access_token}}"}
                            ],
                            "url": {
                                "raw": "{{base_url}}/tracker/picks",
                                "host": ["{{base_url}}"],
                                "path": ["tracker", "picks"]
                            }
                        }
                    },
                    {
                        "name": "Track a Pick",
                        "request": {
                            "method": "POST",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{access_token}}"},
                                {"key": "Content-Type", "value": "application/json"}
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": '{\n  "game_id": 1,\n  "pick_type": "spread",\n  "pick_value": "Lakers -3.5",\n  "odds": -110,\n  "stake": 100,\n  "source": "manual"\n}'
                            },
                            "url": {
                                "raw": "{{base_url}}/tracker/picks",
                                "host": ["{{base_url}}"],
                                "path": ["tracker", "picks"]
                            }
                        }
                    }
                ]
            },
            {
                "name": "Analytics",
                "item": [
                    {
                        "name": "Edge Tracker",
                        "request": {
                            "method": "GET",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{access_token}}"}
                            ],
                            "url": {
                                "raw": "{{base_url}}/analytics/edge-tracker?sport=NBA",
                                "host": ["{{base_url}}"],
                                "path": ["analytics", "edge-tracker"],
                                "query": [
                                    {"key": "sport", "value": "NBA"}
                                ]
                            }
                        }
                    },
                    {
                        "name": "Find Arbitrage",
                        "request": {
                            "method": "GET",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{access_token}}"}
                            ],
                            "url": {
                                "raw": "{{base_url}}/analytics/arbitrage",
                                "host": ["{{base_url}}"],
                                "path": ["analytics", "arbitrage"]
                            }
                        }
                    }
                ]
            },
            {
                "name": "Player Props",
                "item": [
                    {
                        "name": "Get Prediction",
                        "request": {
                            "method": "POST",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{access_token}}"},
                                {"key": "Content-Type", "value": "application/json"}
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": '{\n  "player_name": "LeBron James",\n  "prop_type": "points",\n  "line": 25.5,\n  "sport": "NBA"\n}'
                            },
                            "url": {
                                "raw": "{{base_url}}/player-props/predict",
                                "host": ["{{base_url}}"],
                                "path": ["player-props", "predict"]
                            }
                        }
                    },
                    {
                        "name": "Find Value Props",
                        "request": {
                            "method": "GET",
                            "header": [
                                {"key": "Authorization", "value": "Bearer {{access_token}}"}
                            ],
                            "url": {
                                "raw": "{{base_url}}/player-props/value?sport=NBA",
                                "host": ["{{base_url}}"],
                                "path": ["player-props", "value"],
                                "query": [
                                    {"key": "sport", "value": "NBA"}
                                ]
                            }
                        }
                    }
                ]
            },
            {
                "name": "Health",
                "item": [
                    {
                        "name": "Health Check",
                        "request": {
                            "method": "GET",
                            "url": {
                                "raw": "{{base_url}}/health",
                                "host": ["{{base_url}}"],
                                "path": ["health"]
                            }
                        }
                    },
                    {
                        "name": "Cache Stats",
                        "request": {
                            "method": "GET",
                            "url": {
                                "raw": "{{base_url}}/health/cache",
                                "host": ["{{base_url}}"],
                                "path": ["health", "cache"]
                            }
                        }
                    },
                    {
                        "name": "Rate Limit Stats",
                        "request": {
                            "method": "GET",
                            "url": {
                                "raw": "{{base_url}}/health/rate-limit",
                                "host": ["{{base_url}}"],
                                "path": ["health", "rate-limit"]
                            }
                        }
                    }
                ]
            }
        ]
    }


@router.get("/postman")
def get_postman_collection(request: Request):
    """
    Export API as a Postman collection.

    Import this JSON into Postman to get a ready-to-use collection
    with all endpoints, authentication, and example requests.

    The collection includes:
    - Pre-configured authentication (Bearer token)
    - Auto-token storage after login/register
    - Example request bodies
    - Environment variables for base_url and tokens
    """
    return generate_postman_collection(request)


@router.get("/postman/download")
def download_postman_collection(request: Request):
    """
    Download the Postman collection as a JSON file.
    """
    collection = generate_postman_collection(request)

    return JSONResponse(
        content=collection,
        media_type="application/json",
        headers={
            "Content-Disposition": "attachment; filename=edgebet-api-collection.json"
        }
    )


# =============================================================================
# API Examples
# =============================================================================

API_EXAMPLES = {
    "games": {
        "list": {
            "description": "Get list of upcoming games for a sport",
            "endpoint": "GET /games?sport=NBA",
            "response": {
                "games": [
                    {
                        "id": 1,
                        "sport": "NBA",
                        "home_team": "Los Angeles Lakers",
                        "away_team": "Boston Celtics",
                        "start_time": "2024-01-15T19:30:00Z",
                        "odds": {
                            "spread": {"home": -3.5, "away": 3.5},
                            "moneyline": {"home": -150, "away": 130},
                            "total": {"over": 225.5, "under": 225.5}
                        }
                    }
                ]
            }
        }
    },
    "recommendations": {
        "run": {
            "description": "Generate betting recommendations based on edge analysis",
            "endpoint": "POST /recommendations/run",
            "request": {
                "client_id": 1,
                "sports": ["NBA", "NFL"],
                "min_edge": 0.05
            },
            "response": {
                "recommendations": [
                    {
                        "game_id": 1,
                        "pick": "Lakers -3.5",
                        "edge": 0.08,
                        "confidence": 0.72,
                        "kelly_fraction": 0.15,
                        "suggested_stake": 150.0,
                        "explanation": "Strong value on Lakers spread based on power ratings..."
                    }
                ],
                "total_suggested_stake": 150.0,
                "generated_at": "2024-01-15T10:00:00Z"
            }
        }
    },
    "player_props": {
        "predict": {
            "description": "Get prediction for a player prop bet",
            "endpoint": "POST /player-props/predict",
            "request": {
                "player_name": "LeBron James",
                "prop_type": "points",
                "line": 25.5,
                "sport": "NBA"
            },
            "response": {
                "player": "LeBron James",
                "prop_type": "points",
                "line": 25.5,
                "prediction": 27.3,
                "over_probability": 0.62,
                "edge": 0.08,
                "recommendation": "OVER",
                "confidence": "medium",
                "factors": {
                    "recent_average": 26.8,
                    "vs_opponent": 28.1,
                    "rest_days": 2
                }
            }
        }
    }
}


@router.get("/examples")
def get_api_examples():
    """
    Get example requests and responses for common API operations.
    """
    return {
        "title": "API Examples",
        "description": "Example requests and responses for common operations",
        "examples": API_EXAMPLES
    }


@router.get("/examples/{category}")
def get_category_examples(category: str):
    """
    Get examples for a specific API category.
    """
    if category not in API_EXAMPLES:
        return JSONResponse(
            status_code=404,
            content={"detail": f"Category '{category}' not found. Available: {list(API_EXAMPLES.keys())}"}
        )

    return {
        "category": category,
        "examples": API_EXAMPLES[category]
    }
