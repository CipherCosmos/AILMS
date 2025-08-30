from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from database import get_fs_bucket, _uuid
from auth import _current_user

files_router = APIRouter()

@files_router.post("/upload")
async def upload_file(file: UploadFile = File(...), user=Depends(_current_user)):
    file_id = _uuid()
    fs_bucket = get_fs_bucket()
    grid_in = fs_bucket.open_upload_stream_with_id(file_id, file.filename, metadata={"user_id": user["id"], "content_type": file.content_type})
    while True:
        chunk = await file.read(1024 * 512)
        if not chunk:
            break
        await grid_in.write(chunk)
    await grid_in.close()
    return {"file_id": file_id, "filename": file.filename}

@files_router.get("/{file_id}")
async def download_file(file_id: str, user=Depends(_current_user)):
    try:
        fs_bucket = get_fs_bucket()
        grid_out = await fs_bucket.open_download_stream(file_id)
    except Exception:
        raise HTTPException(404, "File not found")
    headers = {"Content-Disposition": f"attachment; filename={grid_out.filename}"}
    async def file_iterator():
        while True:
            chunk = await grid_out.readchunk()
            if not chunk:
                break
            yield chunk
    return StreamingResponse(file_iterator(), headers=headers, media_type=grid_out.metadata.get("content_type", "application/octet-stream"))