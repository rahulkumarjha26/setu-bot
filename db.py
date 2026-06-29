import os
import uuid
from supabase import create_client
from config import (
    SUPABASE_URL, SUPABASE_SERVICE_KEY, MEDIA_BUCKET,
    R2_ENDPOINT, R2_ACCESS_KEY, R2_SECRET_KEY, R2_BUCKET, R2_PUBLIC_URL
)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# R2 client (S3-compatible) — falls back to Supabase storage if not configured
_r2 = None
_r2_bucket = R2_BUCKET
_r2_public = R2_PUBLIC_URL.rstrip("/") if R2_PUBLIC_URL else ""
if R2_ENDPOINT and R2_ACCESS_KEY and R2_SECRET_KEY:
    import boto3
    from botocore.client import Config
    _r2 = boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def upload_media(local_path: str, media_type: str) -> str:
    """Upload a file and return its public URL. Uses R2 if configured, else Supabase Storage."""
    ext = local_path.rsplit(".", 1)[-1]
    key = f"{media_type}/{uuid.uuid4()}.{ext}"
    if _r2:
        ctype = {"jpg":"image/jpeg","mp4":"video/mp4","ogg":"audio/ogg","mp3":"audio/mpeg"}.get(ext,"application/octet-stream")
        _r2.upload_file(local_path, _r2_bucket, key, ExtraArgs={"ContentType": ctype})
        return f"{_r2_public}/{key}"
    # Fallback to Supabase Storage
    with open(local_path, "rb") as f:
        supabase.storage.from_(MEDIA_BUCKET).upload(
            key, f.read(), {"content-type": "application/octet-stream"}
        )
    return supabase.storage.from_(MEDIA_BUCKET).get_public_url(key)


def insert_problem(record: dict) -> str:
    """Insert a problem row, return its id."""
    res = supabase.table("problems").insert(record).execute()
    return res.data[0]["id"]


def update_status(problem_id: str, status: str) -> None:
    supabase.table("problems").update({"status": status}).eq("id", problem_id).execute()


def update_problem_field(problem_id: str, field: str, value) -> None:
    supabase.table("problems").update({field: value}).eq("id", problem_id).execute()
