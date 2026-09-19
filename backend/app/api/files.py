import os
import mimetypes
from datetime import datetime
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.workspace.manager import get_workspace_manager

router = APIRouter(prefix="/files", tags=["Files"])
SKIP_DIRS = {".git", "node_modules", ".next", "__pycache__", ".venv", "venv"}

def _file_info(path: str):
    ws = get_workspace_manager()
    full = ws.resolve_path(path)
    if not os.path.isfile(full):
        return None
    stat = os.stat(full)
    rel = ws.get_relative_path(full)
    mime, _ = mimetypes.guess_type(full)
    ext = os.path.splitext(full)[1].lower()
    return {
        "name": os.path.basename(full),
        "path": rel,
        "size": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "mime_type": mime or "application/octet-stream",
        "extension": ext,
        "is_text": bool(mime and (mime.startswith("text/") or mime in {
            "application/json", "application/javascript", "application/xml"
        })) or ext in {
            ".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".html",
            ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".csv",
            ".sql", ".sh", ".bat", ".ps1"
        },
    }

@router.get("/")
def list_files():
    ws = get_workspace_manager()
    items = []
    for current, dirs, filenames in os.walk(ws.root_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for filename in filenames:
            full = os.path.join(current, filename)
            try:
                info = _file_info(ws.get_relative_path(full))
                if info:
                    items.append(info)
            except Exception:
                continue
        if len(items) >= 500:
            break
    # Keep user-uploaded files at the top, then sort everything else naturally.
    items.sort(key=lambda x: (
        0 if x["path"].replace("\\", "/").lower().startswith("uploads/") else 1,
        x["path"].lower()
    ))
    return {"success": True, "files": items[:500], "count": min(len(items), 500)}

@router.get("/content")
def read_file(path: str):
    ws = get_workspace_manager()
    try:
        full = ws.resolve_path(unquote(path))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not os.path.isfile(full):
        raise HTTPException(status_code=404, detail="File not found")
    info = _file_info(path)
    if not info:
        raise HTTPException(status_code=404, detail="File not found")
    if not info["is_text"]:
        return {"success": True, "path": info["path"], "previewable": False, "content": ""}
    try:
        with open(full, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(1024 * 1024)
        return {"success": True, "path": info["path"], "previewable": True, "content": content}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/download")
def download_file(path: str):
    ws = get_workspace_manager()
    try:
        full = ws.resolve_path(unquote(path))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not os.path.isfile(full):
        raise HTTPException(status_code=404, detail="File not found")
    filename = os.path.basename(full)
    media_type = mimetypes.guess_type(full)[0] or "application/octet-stream"
    return FileResponse(
        full,
        filename=filename,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )

@router.post("/upload")
async def upload_file(request: Request, filename: str):
    ws = get_workspace_manager()
    safe_name = os.path.basename(filename.strip())
    if not safe_name or safe_name in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid filename")
    relative_path = os.path.join("uploads", safe_name)
    try:
        full = ws.resolve_path(relative_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    body = await request.body()
    if len(body) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Maximum upload size is 50 MB")
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as f:
        f.write(body)
    return {"success": True, "file": _file_info(relative_path)}
