import asyncio
import json
import logging
from typing import Any, Optional

from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from manager import Manager
import esi.api as esi

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
manager = Manager()

async def start_manager() -> None:
    """Periodically updates the manager in a separate thread to prevent blocking."""
    while True:
        try:
            logger.info("Starting manager update")
            await asyncio.to_thread(manager.update)
            logger.info("Manager update completed")
        except Exception as error:
            logger.exception("An error occurred during manager update: %s", error)
        await asyncio.sleep(2)

@app.on_event("startup")
async def startup_event() -> None:
    """Initializes the manager update task on startup."""
    app.state.manager_task = asyncio.create_task(start_manager())

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allows requests from specified origin
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all HTTP headers
)

@app.get("/")
async def read_root() -> dict:
    """Root endpoint that returns a welcome message."""
    return {"Hello": "World"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Optional[str] = None) -> dict:
    """Retrieves an item by ID, optionally filtering by query parameter `q`."""
    return {"item_id": item_id, "q": q}

@app.get("/route")
async def read_route() -> Any:
    """Returns the current route from the manager."""
    return manager.route

@app.get("/route_info")
async def read_route_info() -> Any:
    """Returns route information from the manager."""
    return manager.route_info

@app.post("/create_route")
async def create_route(background_tasks: BackgroundTasks) -> dict:
    """Initiates route creation in the background."""
    background_tasks.add_task(manager.create_route)
    return {"status": "Route creation initiated"}

@app.get("/data_stream")
async def data_stream() -> StreamingResponse:
    """Streams data updates to the client."""
    async def event_stream() -> Any:
        while True:
            data = {
                "route": manager.route,
                "route_info": manager.route_info,
                "log": manager.log,
            }
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(1)
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.get("/logs")
async def get_logs() -> Any:
    """Retrieves logs from the manager."""
    return manager.log_queue

@app.post("/open_market_window/{type_id}")
async def open_market_window(type_id: int) -> Any:
    """Opens a market window for a given `type_id` using the ESI API."""
    result = esi.open_market_window(type_id)
    logger.info("Opened market window for type_id %s", type_id)
    return result
