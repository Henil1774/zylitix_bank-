from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, dashboard, customers, users

app = FastAPI(
    title="Zylitix Bank API",
    description="Banking REST API — auth, customers, dashboard, users.",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1800", "http://127.0.0.1:1800"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(customers.router)
app.include_router(users.router)

@app.get("/", tags=["Root"])
def root():
    return {"bank": "Zylitix Bank", "api_version": "3.0.0",
            "status": "running", "docs": "http://127.0.0.1:8000/docs"}