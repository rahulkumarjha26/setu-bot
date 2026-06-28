import uuid
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY, MEDIA_BUCKET

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def upload_media(local_path: str, media_type: str) -> str:
    """Upload a file to the public 'media' bucket and return its public URL."""
    ext = local_path.rsplit(".", 1)[-1]
    key = f"{media_type}/{uuid.uuid4()}.{ext}"
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
