from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from playback_snapshotting import save_playback_snapshot, SnapshotFilter

app = FastAPI()


@app.get("/ping")
def ping():
    return {"message": "pong"}

@app.post("/save-playback-snapshot/")
def save_playback_snapshot_endpoint(filter: SnapshotFilter, dry_run: bool = Query(False, description="Run as a dry run (no changes will be made)")):
    snapshot = save_playback_snapshot(filter, dry_run)
    if snapshot:
        return {"message": f"Snapshot {'retrieved' if dry_run else 'saved'} at {snapshot.CurrentPlaybackTimeStamp}"}
    else:
        raise HTTPException(status_code=404, detail="No matching playback snapshot found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10691)