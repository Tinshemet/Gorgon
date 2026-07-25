"""
executor/disk_delivery.py — raw VM disk / bundle delivery for the executor.

Streams a VM's primary qcow2 disk (with SHA-256 + Range support) and the whole VM
folder as a tar.gz, straight off local disk (the executor is authoritative — it owns
the gorgon tree; the orchestrator's image_delivery only proxies these). Kept out of
server.py so that module stays routing + auth.
"""
import hashlib
import json
import os
import pathlib
import subprocess
from typing import Any, Dict, Iterator

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse

from executor.api._vm_constants import VM_BASE_DIR

_CFG = json.load(open(os.path.join(os.path.dirname(__file__), "config.json")))

_VM_BASE   = pathlib.Path(VM_BASE_DIR)
_CHUNK     = _CFG.get("io_chunk_bytes", 4 * 1024 * 1024)   # disk read/stream chunk
_TAR_CHUNK = _CFG.get("tar_chunk_bytes", 65536)            # tar pipe read chunk


def disk_path(vm_name: str) -> pathlib.Path:
    """Return the path to a VM's first qcow2 disk, or raise 404 if absent."""
    vm_dir = _VM_BASE / vm_name
    if not vm_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"VM '{vm_name}' not found.")
    candidates = sorted(vm_dir.glob("*.qcow2"))
    if not candidates:
        raise HTTPException(status_code=404, detail=f"No qcow2 disk for '{vm_name}'.")
    return candidates[0]


def vm_disk_sha256(vm_name: str) -> Dict[str, Any]:
    """Return SHA-256 and size of the VM's primary disk."""
    path = disk_path(vm_name)
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return {"vm_name": vm_name, "disk": path.name,
            "sha256": h.hexdigest(), "size_bytes": path.stat().st_size}


def vm_disk(vm_name: str, request: Request) -> StreamingResponse:
    """Stream the VM's primary qcow2 disk with SHA256 header and Range support."""
    path  = disk_path(vm_name)
    total = path.stat().st_size
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    checksum     = h.hexdigest()
    range_header = request.headers.get("range")
    start, end   = 0, total - 1
    if range_header:
        try:
            _, rng = range_header.split("=")
            s, e   = rng.split("-")
            start  = int(s)
            end    = int(e) if e else total - 1
        except Exception:
            raise HTTPException(status_code=416, detail="Invalid Range header.")
        if start >= total or end >= total or start > end:
            raise HTTPException(status_code=416, detail="Range not satisfiable.")
    length = end - start + 1

    def _stream() -> Iterator[bytes]:
        """Yield a byte range of a file in chunks for HTTP streaming."""
        remaining = length
        with open(path, "rb") as f:
            f.seek(start)
            while remaining > 0:
                data = f.read(min(_CHUNK, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data

    return StreamingResponse(
        _stream(),
        status_code=206 if range_header else 200,
        media_type="application/octet-stream",
        headers={
            "Content-Length":      str(length),
            "Content-Range":       f"bytes {start}-{end}/{total}",
            "Accept-Ranges":       "bytes",
            "X-SHA256":            checksum,
            "X-Disk-Size":         str(total),
            "Content-Disposition": f'attachment; filename="{path.name}"',
        },
    )


def vm_bundle(vm_name: str) -> StreamingResponse:
    """Stream the entire VM folder as a gzipped tar archive."""
    vm_dir = _VM_BASE / vm_name
    if not vm_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"VM '{vm_name}' not found.")

    def _tar_stream() -> Iterator[bytes]:
        """Yield a tar archive of a VM directory as a byte stream."""
        proc = subprocess.Popen(
            ["tar", "czf", "-", "-C", str(vm_dir.parent), vm_name],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        try:
            for chunk in iter(lambda: proc.stdout.read(_TAR_CHUNK), b""):
                yield chunk
        finally:
            proc.stdout.close()
            proc.wait()

    return StreamingResponse(
        _tar_stream(),
        media_type="application/gzip",
        headers={"Content-Disposition": f'attachment; filename="{vm_name}.tar.gz"'},
    )
