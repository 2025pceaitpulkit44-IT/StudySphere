import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import admin, ai, auth, doubts, documents, quiz, student, subjects, undertaking
from app.config import get_settings
from app.ratelimit import limiter

logger = logging.getLogger("studysphere")

app = FastAPI(title="StudySphere API", version="0.1.0", description="Your college knowledge, in one place.")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=False,  # tokens travel in the Authorization header, not cookies
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    # Full detail goes to the server log only; users never see stack traces.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(subjects.router)
app.include_router(undertaking.router)
app.include_router(documents.router)
app.include_router(ai.router)
app.include_router(admin.router)
app.include_router(doubts.router)
app.include_router(quiz.router)
app.include_router(student.router)
