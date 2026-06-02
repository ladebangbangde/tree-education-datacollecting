from fastapi import FastAPI

app = FastAPI(title="tree-education-datacollecting")

@app.get("/api/v1/health")
def health():
    return {"code": 0, "message": "ok", "data": {"status": "UP"}}
