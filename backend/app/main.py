from fastapi import FastAPI

from app.routers import auth, users, conversations

app = FastAPI(
    title="SalesLoop AI",
    description="Plateforme d'agents conversationnels pour équipes commerciales",
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(conversations.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}