from fastapi import FastAPI
from pydantic import BaseModel
import os
import shlex
from urllib.parse import urlparse

app = FastAPI()

WORKSPACE = "/home/agent/workspace"
HOME = "/home/agent"
SECRET = "/home/agent/.bashrc"
WRITE_ROOT = "/data/agent/outbox"
ALLOWED_HOSTS = {"pypi.org", "huggingface.co"}


class RequestData(BaseModel):
    tool: str
    command: str | None = None
    path: str | None = None
    content: str | None = None
    method: str | None = None
    url: str | None = None


def normalize_path(path: str):
    path = path.replace("$HOME", HOME)

    if path.startswith("~"):
        path = path.replace("~", HOME, 1)

    if not os.path.isabs(path):
        path = os.path.join(WORKSPACE, path)

    return os.path.normpath(path)


def inside(root, path):
    root = os.path.normpath(root)
    path = os.path.normpath(path)
    return path == root or path.startswith(root + os.sep)


@app.post("/check")
def check(req: RequestData):

    if req.tool == "bash":

        cmd = req.command or ""
        cmd = cmd.replace("$HOME", HOME).replace("~", HOME)

        try:
            tokens = shlex.split(cmd)
        except:
            tokens = cmd.split()

        for t in tokens:
            p = normalize_path(t)
            if p == SECRET:
                return {
                    "decision": "block",
                    "reason": "restricted file"
                }

        if SECRET in cmd:
            return {
                "decision": "block",
                "reason": "restricted file"
            }

        return {
            "decision": "allow",
            "reason": "ok"
        }

    elif req.tool == "write_file":

        p = normalize_path(req.path or "")

        if inside(WRITE_ROOT, p):
            return {
                "decision": "allow",
                "reason": "ok"
            }

        return {
            "decision": "block",
            "reason": "outside write directory"
        }

    elif req.tool == "http_request":

        host = (urlparse(req.url or "").hostname or "").lower()

        if host in ALLOWED_HOSTS:
            return {
                "decision": "allow",
                "reason": "ok"
            }

        return {
            "decision": "block",
            "reason": "host not allowed"
        }

    return {
        "decision": "allow",
        "reason": "ok"
    }