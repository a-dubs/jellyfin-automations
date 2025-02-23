
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from playback_snapshotting import save_playback_snapshot, SnapshotFilter

app = FastAPI()


@app.get("/ping")
def ping():
    return {"message": "pong"}

@app.post("/save-playback-snapshot/")
def save_playback_snapshot_endpoint(filter: SnapshotFilter):

    snapshot = save_playback_snapshot(filter)
    if snapshot:
        return {"message": f"Snapshot saved at {snapshot.CurrentPlaybackTimeStamp}"}
    else:
        raise HTTPException(status_code=404, detail="No matching playback snapshot found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10691)