from fastapi import FastAPI

app = FastAPI(title="Payments Service")


@app.get("/")
async def hello_world():
    return {"message": "Hello World"}
