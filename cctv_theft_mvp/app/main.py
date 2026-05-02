from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from .analyzer import AnalyzerError, run_theft_analysis
from .config import settings
from .models import AnalyzeParams, CreateJobResponse, JobDetail, JobStatus
from .store import JobRecord, JobStore

app = FastAPI(title="CCTV Theft MVP API", version="0.1.0")
store = JobStore()
ui_file = Path(__file__).resolve().parent / "static" / "index.html"


def _load_params(params_json: str | None) -> AnalyzeParams:
    if not params_json:
        return AnalyzeParams(
            detector_engine=settings.detector_engine,
            detector_model=settings.detector_model,
            detector_conf=settings.detector_conf,
        )
    try:
        raw = json.loads(params_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid params JSON: {exc.msg}") from exc
    return AnalyzeParams(**raw)


def _run_job(job_id: str, params: AnalyzeParams) -> None:
    record = store.get(job_id)
    if record is None:
        return
    store.set_status(job_id, JobStatus.running)
    output_video_path = settings.output_dir / f"{job_id}.mp4"
    report_path = settings.output_dir / f"{job_id}.json"
    try:
        result = run_theft_analysis(record.video_path, output_video_path, report_path, params)
        store.set_success(job_id, result.output_video_path, result.report_path, result.events)
    except AnalyzerError as exc:
        store.set_failed(job_id, str(exc))
    except Exception as exc:
        store.set_failed(job_id, f"Unexpected error: {exc}")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse, response_model=None)
@app.get("/ui", response_class=HTMLResponse, response_model=None)
def ui():
    if not ui_file.exists():
        return HTMLResponse("UI file not found. Expected app/static/index.html", status_code=404)
    return FileResponse(ui_file)


@app.post("/v1/jobs", response_model=CreateJobResponse)
async def create_job(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    params: str | None = Form(default=None),
) -> CreateJobResponse:
    if not video.filename:
        raise HTTPException(status_code=400, detail="Video filename is required")

    ext = Path(video.filename).suffix.lower() or ".mp4"
    if ext not in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
        raise HTTPException(status_code=400, detail="Allowed video types: mp4, mov, avi, mkv, webm")

    job_id = str(uuid.uuid4())
    job_dir = settings.jobs_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    video_path = job_dir / f"input{ext}"
    video_path.write_bytes(await video.read())

    analyze_params = _load_params(params)
    store.create(JobRecord(job_id=job_id, video_path=video_path))
    background_tasks.add_task(_run_job, job_id, analyze_params)
    return CreateJobResponse(job_id=job_id, status=JobStatus.queued)


@app.get("/v1/jobs/{job_id}", response_model=JobDetail)
def get_job(job_id: str) -> JobDetail:
    record = store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return record.to_detail()


@app.get("/v1/jobs/{job_id}/result")
def download_result(job_id: str) -> FileResponse:
    record = store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if record.status != JobStatus.succeeded or not record.output_video_path:
        raise HTTPException(status_code=409, detail=f"Job is {record.status}")
    return FileResponse(record.output_video_path, media_type="video/mp4", filename=record.output_video_path.name)


@app.get("/v1/jobs/{job_id}/report")
def download_report(job_id: str) -> FileResponse:
    record = store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if record.status != JobStatus.succeeded or not record.report_path:
        raise HTTPException(status_code=409, detail=f"Job is {record.status}")
    return FileResponse(record.report_path, media_type="application/json", filename=record.report_path.name)

