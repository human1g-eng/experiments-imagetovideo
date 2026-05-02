from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .models import AnalysisResult, AnalyzeParams


class AnalyzerError(RuntimeError):
    pass


@dataclass
class Detection:
    x1: float
    y1: float
    x2: float
    y2: float
    conf: float

    @property
    def cx(self) -> float:
        return (self.x1 + self.x2) / 2.0

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2.0


@dataclass
class TrackState:
    track_id: int
    bbox: Detection
    missed: int = 0
    prev_cx: float = 0.0
    prev_cy: float = 0.0
    crossed_counter: bool = False
    loiter_frames: int = 0
    loiter_alerted: bool = False
    grab_exit_alerted: bool = False
    reach_alert_cooldown: int = 0

    def __post_init__(self) -> None:
        self.prev_cx = self.bbox.cx
        self.prev_cy = self.bbox.cy


class Detector:
    def detect(self, frame: np.ndarray) -> list[Detection]:
        raise NotImplementedError


class HogDetector(Detector):
    def __init__(self) -> None:
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detect(self, frame: np.ndarray) -> list[Detection]:
        rects, weights = self.hog.detectMultiScale(
            frame,
            winStride=(4, 4),
            padding=(8, 8),
            scale=1.03,
        )
        detections: list[Detection] = []
        for (x, y, w, h), weight in zip(rects, weights):
            detections.append(Detection(float(x), float(y), float(x + w), float(y + h), float(weight)))
        return detections


class YoloDetector(Detector):
    def __init__(self, model_name: str, conf: float) -> None:
        from ultralytics import YOLO  # type: ignore

        self.model = YOLO(model_name)
        self.conf = conf

    def detect(self, frame: np.ndarray) -> list[Detection]:
        result = self.model.predict(frame, classes=[0], conf=self.conf, verbose=False)[0]
        detections: list[Detection] = []
        if result.boxes is None:
            return detections
        xyxy = result.boxes.xyxy.cpu().numpy()
        confs = result.boxes.conf.cpu().numpy()
        for box, conf in zip(xyxy, confs):
            detections.append(Detection(float(box[0]), float(box[1]), float(box[2]), float(box[3]), float(conf)))
        return detections


def _build_detector(params: AnalyzeParams) -> tuple[Detector, str]:
    engine = params.detector_engine.lower()
    if engine == "hog":
        return HogDetector(), "hog"

    if engine in {"auto", "yolo"}:
        try:
            return YoloDetector(params.detector_model, params.detector_conf), "yolo"
        except Exception:
            if engine == "yolo":
                raise AnalyzerError(
                    "YOLO detector requested but unavailable. Install ultralytics + torch, "
                    "or switch detector_engine to 'hog'."
                )
            return HogDetector(), "hog"

    raise AnalyzerError(f"Unsupported detector_engine={params.detector_engine}")


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _track_match(
    tracks: dict[int, TrackState],
    detections: list[Detection],
    max_distance_px: float,
    max_missed: int,
    next_track_id: int,
) -> tuple[dict[int, TrackState], int]:
    unmatched_dets = set(range(len(detections)))
    matched_tracks: set[int] = set()

    for track_id, track in list(tracks.items()):
        best_idx = -1
        best_dist = float("inf")
        for det_idx in unmatched_dets:
            det = detections[det_idx]
            dist = _distance((track.bbox.cx, track.bbox.cy), (det.cx, det.cy))
            if dist < best_dist and dist <= max_distance_px:
                best_dist = dist
                best_idx = det_idx

        if best_idx >= 0:
            det = detections[best_idx]
            track.prev_cx = track.bbox.cx
            track.prev_cy = track.bbox.cy
            track.bbox = det
            track.missed = 0
            matched_tracks.add(track_id)
            unmatched_dets.remove(best_idx)
        else:
            track.missed += 1

    for det_idx in unmatched_dets:
        det = detections[det_idx]
        tracks[next_track_id] = TrackState(track_id=next_track_id, bbox=det)
        next_track_id += 1

    for track_id in list(tracks.keys()):
        if tracks[track_id].missed > max_missed:
            del tracks[track_id]

    return tracks, next_track_id


def _draw_overlays(
    frame: np.ndarray,
    tracks: dict[int, TrackState],
    counter_line_y: int,
    counter_band: int,
    exit_zone_width: int,
) -> None:
    h, w = frame.shape[:2]
    cv2.line(frame, (0, counter_line_y), (w, counter_line_y), (0, 200, 255), 2)
    cv2.rectangle(frame, (0, max(counter_line_y - counter_band, 0)), (w, min(counter_line_y + counter_band, h - 1)), (0, 80, 80), 1)
    cv2.rectangle(frame, (0, 0), (exit_zone_width, h - 1), (200, 120, 0), 2)
    cv2.rectangle(frame, (w - exit_zone_width, 0), (w - 1, h - 1), (200, 120, 0), 2)
    cv2.putText(frame, "Counter line", (10, max(counter_line_y - 8, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 255), 2)
    cv2.putText(frame, "Exit zones", (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 120, 0), 2)

    for track in tracks.values():
        color = (0, 255, 0)
        if track.crossed_counter:
            color = (0, 140, 255)
        if track.grab_exit_alerted:
            color = (0, 0, 255)
        x1, y1, x2, y2 = int(track.bbox.x1), int(track.bbox.y1), int(track.bbox.x2), int(track.bbox.y2)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            frame,
            f"ID {track.track_id}",
            (x1, max(y1 - 8, 16)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
        )


def run_theft_analysis(video_path: Path, output_video_path: Path, report_path: Path, params: AnalyzeParams) -> AnalysisResult:
    detector, detector_name = _build_detector(params)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise AnalyzerError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if width <= 0 or height <= 0:
        raise AnalyzerError("Invalid video size")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_video_path), fourcc, fps, (width, height))
    if not out.isOpened():
        raise AnalyzerError(f"Could not create output video: {output_video_path}")

    counter_line_y = int(height * params.counter_line_ratio)
    counter_band = int(height * params.counter_band_ratio)
    exit_zone_width = int(width * params.exit_zone_width_ratio)
    dwell_frames_threshold = int((params.dwell_seconds * fps) / params.process_every_n_frames)

    tracks: dict[int, TrackState] = {}
    next_track_id = 1
    events: list[dict[str, Any]] = []

    frame_idx = -1
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame_idx += 1

        if frame_idx % params.process_every_n_frames == 0:
            detections = detector.detect(frame)
            tracks, next_track_id = _track_match(
                tracks,
                detections,
                max_distance_px=params.match_distance_px,
                max_missed=params.max_track_missed,
                next_track_id=next_track_id,
            )

            for track in tracks.values():
                if track.missed > 0:
                    continue

                cx = track.bbox.cx
                cy = track.bbox.cy
                vx = (cx - track.prev_cx) * fps / params.process_every_n_frames
                vy = (cy - track.prev_cy) * fps / params.process_every_n_frames
                speed = math.hypot(vx, vy)

                in_counter_band = abs(cy - counter_line_y) <= counter_band
                crossing_line = track.bbox.y1 < counter_line_y < track.bbox.y2
                in_exit_zone = cx <= exit_zone_width or cx >= (width - exit_zone_width)

                if in_counter_band:
                    track.loiter_frames += 1
                else:
                    track.loiter_frames = max(0, track.loiter_frames - 1)

                if crossing_line:
                    track.crossed_counter = True
                    if track.reach_alert_cooldown <= 0:
                        events.append(
                            {
                                "type": "counter_reach",
                                "track_id": track.track_id,
                                "time_sec": round(frame_idx / fps, 2),
                                "severity": "medium",
                                "details": "Person body crosses counter line.",
                            }
                        )
                        track.reach_alert_cooldown = int(fps * 3 / params.process_every_n_frames)

                if track.reach_alert_cooldown > 0:
                    track.reach_alert_cooldown -= 1

                if track.loiter_frames >= dwell_frames_threshold and not track.loiter_alerted:
                    track.loiter_alerted = True
                    events.append(
                        {
                            "type": "counter_loitering",
                            "track_id": track.track_id,
                            "time_sec": round(frame_idx / fps, 2),
                            "severity": "medium",
                            "details": f"Person stayed near counter for about {params.dwell_seconds:.1f}s.",
                        }
                    )

                if track.crossed_counter and in_exit_zone and speed >= params.min_speed_px_per_sec and not track.grab_exit_alerted:
                    track.grab_exit_alerted = True
                    events.append(
                        {
                            "type": "grab_and_exit_risk",
                            "track_id": track.track_id,
                            "time_sec": round(frame_idx / fps, 2),
                            "severity": "high",
                            "details": f"Counter interaction followed by fast movement to exit zone ({speed:.1f}px/s).",
                        }
                    )

        _draw_overlays(frame, tracks, counter_line_y, counter_band, exit_zone_width)
        cv2.putText(
            frame,
            f"Detector: {detector_name.upper()} | Events: {len(events)}",
            (10, height - 14),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
        )
        out.write(frame)

    cap.release()
    out.release()

    report = {
        "video_path": str(video_path),
        "output_video_path": str(output_video_path),
        "detector": detector_name,
        "total_events": len(events),
        "events": events,
        "params": params.model_dump(),
    }
    report_path.write_text(json.dumps(report, indent=2))
    return AnalysisResult(output_video_path=output_video_path, report_path=report_path, events=events)

