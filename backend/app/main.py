from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import close_pool, get_cursor
from .routers import flow, prices, production


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The connection pool is initialized lazily on first query (see db.py),
    # not here — the database may not be up yet when the API container
    # starts (e.g. during docker-compose startup), and the API should still
    # boot and report itself as "degraded" via /health rather than crash.
    yield
    close_pool()


app = FastAPI(
    title="Kraft-analyse API",
    description="API for spotpriser i det norske og europeiske kraftmarkedet.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(prices.router)
app.include_router(production.router)
app.include_router(flow.router)


@app.get("/health")
def health():
    """Liveness check. Verifies the API can reach the database."""
    try:
        with get_cursor() as cur:
            cur.execute("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": db_ok}
