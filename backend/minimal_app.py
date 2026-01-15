"""Serveur ultra minimal pour test"""
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Server is running"}

@app.get("/health")
def health():
    return {"healthy": True}

if __name__ == "__main__":
    import uvicorn
    print("Starting minimal server on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
