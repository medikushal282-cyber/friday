import os
import time
import mimetypes
import webbrowser
from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel
from pathlib import Path
from typing import Optional

from app.workspace.manager import get_workspace_manager

router = APIRouter(prefix="/preview", tags=["Preview"])

LAST_UPDATE_TIME = time.time()

def notify_file_change():
    global LAST_UPDATE_TIME
    LAST_UPDATE_TIME = time.time()

LIVE_RELOAD_SCRIPT = """
<!-- frAIday Live Sync Agentic Preview Script -->
<script>
(() => {
  let lastSeen = Date.now() / 1000;
  const poll = async () => {
    try {
      const res = await fetch('/api/preview/reload-check?since=' + lastSeen);
      if (res.ok) {
        const data = await res.json();
        if (data.reload) {
          console.log('[frAIday Live Preview] Detected file change, reloading...');
          window.location.reload();
          return;
        }
      }
    } catch (e) {}
    setTimeout(poll, 800);
  };
  setTimeout(poll, 800);
})();
</script>
"""

class OpenBrowserRequest(BaseModel):
    file_path: str
    browser: Optional[str] = None  # 'default', 'chrome', 'chromium', etc.

@router.get("/reload-check")
async def reload_check(since: float = Query(...)):
    global LAST_UPDATE_TIME
    should_reload = LAST_UPDATE_TIME > since
    return {"reload": should_reload, "timestamp": LAST_UPDATE_TIME}

@router.post("/notify-update")
async def trigger_update():
    notify_file_change()
    return {"status": "ok", "timestamp": LAST_UPDATE_TIME}

@router.post("/open")
async def open_in_browser(req: OpenBrowserRequest):
    """Launches the preview URL in the system browser or Chromium."""
    wm = get_workspace_manager()
    abs_path = Path(wm.resolve_path(req.file_path))
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {req.file_path}")
    
    url = f"http://localhost:8000/api/preview/{req.file_path}"
    try:
        # Try opening via Python webbrowser module (opens default browser e.g. Chrome/Chromium/Edge)
        opened = webbrowser.open(url)
        return {"status": "opened", "url": url, "success": opened}
    except Exception as e:
        return {"status": "error", "message": str(e), "url": url}

@router.get("/{file_path:path}")
async def serve_preview_file(file_path: str):
    wm = get_workspace_manager()
    abs_path = Path(wm.resolve_path(file_path))
    
    # If path is directory or empty, check for index.html
    if abs_path.is_dir():
        index_cand = abs_path / "index.html"
        if index_cand.exists():
            abs_path = index_cand
        else:
            raise HTTPException(status_code=404, detail=f"Directory specified without index.html: {file_path}")
            
    if not abs_path.exists() or not abs_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
    mime_type, _ = mimetypes.guess_type(str(abs_path))
    mime_type = mime_type or "application/octet-stream"

    # For HTML files, inject the live reload script right before </body>
    if mime_type == "text/html" or abs_path.suffix.lower() in [".html", ".htm"]:
        content = abs_path.read_text(encoding="utf-8", errors="replace")
        if "</body>" in content:
            content = content.replace("</body>", f"{LIVE_RELOAD_SCRIPT}\n</body>")
        else:
            content += f"\n{LIVE_RELOAD_SCRIPT}"
        return HTMLResponse(content=content)

    return FileResponse(abs_path, media_type=mime_type)
