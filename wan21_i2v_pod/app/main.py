from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from .config import settings
from .models import CreateJobResponse, InferenceParams, JobDetail, JobStatus
from .runner import RunnerError, run_wan_i2v
from .store import JobRecord, JobStore

app = FastAPI(title="Wan2.1 I2V Pod API", version="0.1.0")
store = JobStore()
ui_file = Path(__file__).resolve().parent / "static" / "index.html"


def _load_params(params_json: str | None) -> InferenceParams:
    if not params_json:
        return InferenceParams(prompt="", size=settings.default_size, seed=settings.default_seed)
    try:
        raw = json.loads(params_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid params JSON: {exc.msg}") from exc
    return InferenceParams(**raw)


def _run_job(job_id: str, params: InferenceParams) -> None:
    record = store.get(job_id)
    if record is None:
        return
    store.set_status(job_id, JobStatus.running)
    output_path = settings.output_dir / f"{job_id}.mp4"
    try:
        result = run_wan_i2v(record.image_path, output_path, params)
        store.set_success(job_id, result.output_path)
    except RunnerError as exc:
        store.set_failed(job_id, str(exc))
    except Exception as exc:
        store.set_failed(job_id, f"Unexpected error: {exc}")


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {"status": "ok", "mock_mode": settings.mock_mode}


@app.get("/", response_class=HTMLResponse, response_model=None)
@app.get("/ui", response_class=HTMLResponse, response_model=None)
def ui():
    if not ui_file.exists():
        return HTMLResponse("UI file not found. Expected app/static/index.html", status_code=404)
    return FileResponse(ui_file)


@app.post("/v1/jobs", response_model=CreateJobResponse)
async def create_job(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(...),
    prompt: str = Form(...),
    params: str | None = Form(default=None),
) -> CreateJobResponse:
    if not image.filename:
        raise HTTPException(status_code=400, detail="Image filename is required")

    ext = Path(image.filename).suffix.lower() or ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=400, detail="Allowed image types: jpg, jpeg, png, webp")

    job_id = str(uuid.uuid4())
    job_dir = settings.jobs_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    image_path = job_dir / f"input{ext}"
    image_path.write_bytes(await image.read())

    job_params = _load_params(params)
    job_params.prompt = prompt

    store.create(JobRecord(job_id=job_id, prompt=prompt, image_path=image_path))
    background_tasks.add_task(_run_job, job_id, job_params)
    return CreateJobResponse(job_id=job_id, status=JobStatus.queued)


@app.get("/v1/jobs/{job_id}", response_model=JobDetail)
def get_job(job_id: str) -> JobDetail:
    record = store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return record.to_detail()


@app.get("/v1/jobs/{job_id}/result")
def download_job(job_id: str) -> FileResponse:
    record = store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if record.status != JobStatus.succeeded or not record.output_path:
        raise HTTPException(status_code=409, detail=f"Job is {record.status}")
    return FileResponse(record.output_path, media_type="video/mp4", filename=record.output_path.name)
