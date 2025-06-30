from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, receipts, password_reset, messages
from app.config import API_PREFIX
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RioCaja Smart API",
    description="API para gestion de comprobantes y usuarios",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=f"{API_PREFIX}/auth", tags=["Auth"])
app.include_router(receipts.router, prefix=f"{API_PREFIX}/receipts", tags=["Receipts"])
app.include_router(password_reset.router, prefix=f"{API_PREFIX}/password-reset", tags=["Password Reset"])
app.include_router(messages.router, prefix=f"{API_PREFIX}/messages", tags=["Messages"])

@app.get("/")
async def root():
    return {
        "message": "RioCaja Smart API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    from app.config import HOST, PORT
    uvicorn.run(app, host=HOST, port=PORT)