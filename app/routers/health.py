from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "Multi-Sport Betting Agent API is running",
        "disclaimer": "SIMULATION ONLY - For educational purposes. No real money wagering."
    }
