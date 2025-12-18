from fastapi import FastAPI

from .routers import athletes, auth, plans, sessions, dashboard

app = FastAPI(
    title="Athletics Training Platform",
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(athletes.router)
app.include_router(plans.router)
app.include_router(sessions.router)
app.include_router(dashboard.router)


@app.get("/health", tags=["health"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
