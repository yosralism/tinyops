from fastapi import FastAPI

app = FastAPI(title="tinyops", version="0.1.0")


@app.get("/health", tags=["system"])
async def health_check():
    return {
        "status": "ok",
        "service": "tinyops-api",
        "version": "0.1.0",
    }