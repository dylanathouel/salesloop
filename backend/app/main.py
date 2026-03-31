from fastapi import FastAPI

app = FastAPI(
    title="SalesLoop AI",
    description="Plateforme d'agents conversationnels pour équipes commerciales",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}