import os
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from playback_snapshotting import save_playback_snapshot, SnapshotFilter
from logging_setup import get_logger

app_logger = get_logger('server')

app = FastAPI()

@app.get("/ping")
def ping():
    app_logger.info("Ping endpoint called")
    return {"message": "pong"}

@app.post("/save-playback-snapshot/")
def save_playback_snapshot_endpoint(filter: SnapshotFilter, dry_run: bool = Query(False, description="Run as a dry run (no changes will be made)")):
    app_logger.info(f"Save playback snapshot endpoint called with filter: {filter} and dry_run: {dry_run}")
    try:
        snapshot = save_playback_snapshot(filter, dry_run)
        if snapshot:
            message = f"Snapshot {'retrieved' if dry_run else 'saved'} at {snapshot.CurrentPlaybackTimeStamp}"
            app_logger.info(message)
            return {"message": message}
        else:
            app_logger.warning("No matching playback snapshot found")
            raise HTTPException(status_code=404, detail="No matching playback snapshot found")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        app_logger.error(f"Unexpected error in save_playback_snapshot_endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

if __name__ == "__main__":
    import uvicorn
    app_logger.info("Starting server")
    uvicorn.run(app, host="0.0.0.0", port=10691, log_config="uvicorn_logging_config.yaml")