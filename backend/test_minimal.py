"""Test minimal pour identifier le crash"""
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello from test server"}

@app.get("/test")
async def test():
    return {"status": "ok"}

if __name__ == "__main__":
    print("Starting minimal test server on port 8002...")
    uvicorn.run(app, host="127.0.0.1", port=8002)
