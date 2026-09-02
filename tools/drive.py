#!/usr/bin/env python3
"""Google Drive helpers: import a resume from Drive, save drafts to Drive.

Deliberately narrow, same shape as the rest of this repo's Google tools:
- Listing/reading uses drive.readonly (any file, read-only).
- Saving uses drive.file (files this app creates only) and is create-only —
  there is no update/overwrite/delete function here. A "save to Drive" call
  always creates a brand-new file; it can never touch anything that already
  exists in the user's Drive.
- Saved drafts land in a "Job Tracker" folder in the user's Drive, under a
  "Resumes" or "Cover Letters" subfolder (see ensure_folders()). The same
  folder also holds the application tracker Sheet (tools/tracker.py).

Usage:
  python tools/drive.py list-resumes
  python tools/drive.py ensure-folders
  python tools/drive.py import-resume --file-id FILE_ID
  python tools/drive.py save-draft --path LOCAL_FILE --name "Cover Letter - Acme" --kind cover_letter
"""

import argparse
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from googleapiclient.discovery import build  # noqa: E402
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload  # noqa: E402

from auth.google_auth import get_credentials  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
RESUME_DIR = REPO_ROOT / "data" / "resume"
CONFIG_PATH = REPO_ROOT / "config" / "tracker.json"  # shared with tools/tracker.py

GOOGLE_DOC_EXPORT_MIME = "application/pdf"
GOOGLE_NATIVE_MIMES = {
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.spreadsheet",
    "application/vnd.google-apps.presentation",
}
FOLDER_MIME = "application/vnd.google-apps.folder"

JOB_TRACKER_FOLDER_NAME = "Job Tracker"
RESUMES_FOLDER_NAME = "Resumes"
COVER_LETTERS_FOLDER_NAME = "Cover Letters"


def _service():
    return build("drive", "v3", credentials=get_credentials())


def _load_config():
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _save_config(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def _find_or_create_folder(name, parent_id=None):
    service = _service()
    query = f"name = '{name}' and mimeType = '{FOLDER_MIME}' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    result = service.files().list(q=query, fields="files(id, name)", pageSize=1).execute()
    existing = result.get("files", [])
    if existing:
        return existing[0]["id"]
    body = {"name": name, "mimeType": FOLDER_MIME}
    if parent_id:
        body["parents"] = [parent_id]
    created = service.files().create(body=body, fields="id").execute()
    return created["id"]


def ensure_folders():
    """Create (or find) the Job Tracker / Resumes / Cover Letters folder
    structure in the user's Drive. Idempotent — safe to call every time; IDs
    are cached in config/tracker.json (gitignored) after the first call."""
    config = _load_config()
    keys = ("job_tracker_folder_id", "resumes_folder_id", "cover_letters_folder_id")
    if all(config.get(k) for k in keys):
        return config

    job_tracker_id = config.get("job_tracker_folder_id") or _find_or_create_folder(JOB_TRACKER_FOLDER_NAME)
    resumes_id = config.get("resumes_folder_id") or _find_or_create_folder(RESUMES_FOLDER_NAME, job_tracker_id)
    cover_letters_id = config.get("cover_letters_folder_id") or _find_or_create_folder(
        COVER_LETTERS_FOLDER_NAME, job_tracker_id
    )

    config.update(
        {
            "job_tracker_folder_id": job_tracker_id,
            "resumes_folder_id": resumes_id,
            "cover_letters_folder_id": cover_letters_id,
        }
    )
    _save_config(config)
    return config


def list_candidate_resumes():
    query = (
        "trashed = false and "
        "(name contains 'resume' or name contains 'Resume' or name contains 'CV') and "
        "(mimeType = 'application/pdf' or "
        "mimeType = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' or "
        "mimeType = 'application/vnd.google-apps.document')"
    )
    result = (
        _service()
        .files()
        .list(q=query, fields="files(id, name, mimeType, modifiedTime)", pageSize=25, orderBy="modifiedTime desc")
        .execute()
    )
    return result.get("files", [])


def import_resume(file_id):
    service = _service()
    meta = service.files().get(fileId=file_id, fields="name, mimeType").execute()
    name, mime = meta["name"], meta["mimeType"]

    buf = io.BytesIO()
    if mime in GOOGLE_NATIVE_MIMES:
        request = service.files().export_media(fileId=file_id, mimeType=GOOGLE_DOC_EXPORT_MIME)
        name = name if name.lower().endswith(".pdf") else f"{name}.pdf"
    else:
        request = service.files().get_media(fileId=file_id)

    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    RESUME_DIR.mkdir(parents=True, exist_ok=True)
    for old in RESUME_DIR.iterdir():
        if old.is_file() and not old.name.startswith("."):
            old.unlink()
    safe_name = Path(name).name
    (RESUME_DIR / safe_name).write_bytes(buf.getvalue())
    return {"saved_as": safe_name, "source_file_id": file_id}


def save_draft(local_path, name, kind, mimetype=None):
    """Upload a local file into Drive as a brand-new file — create-only, never
    overwrites or modifies anything that already exists. `kind` is "resume"
    or "cover_letter" and determines which subfolder of Job Tracker it lands
    in (see ensure_folders())."""
    folder_key = {"resume": "resumes_folder_id", "cover_letter": "cover_letters_folder_id"}.get(kind)
    if not folder_key:
        raise ValueError('kind must be "resume" or "cover_letter"')
    parent_id = ensure_folders()[folder_key]

    local_path = Path(local_path)
    mimetype = mimetype or "application/octet-stream"
    media = MediaIoBaseUpload(io.BytesIO(local_path.read_bytes()), mimetype=mimetype)
    file = (
        _service()
        .files()
        .create(body={"name": name, "parents": [parent_id]}, media_body=media, fields="id, name, webViewLink")
        .execute()
    )
    return file


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-resumes", help="Search Drive for candidate resume files")
    sub.add_parser("ensure-folders", help="Create/find the Job Tracker folder structure, print its IDs")

    p_import = sub.add_parser("import-resume", help="Download a Drive file into data/resume/")
    p_import.add_argument("--file-id", required=True)

    p_save = sub.add_parser("save-draft", help="Upload a local file into Job Tracker/Resumes or /Cover Letters")
    p_save.add_argument("--path", required=True)
    p_save.add_argument("--name", required=True)
    p_save.add_argument("--kind", required=True, choices=["resume", "cover_letter"])
    p_save.add_argument("--mimetype", default=None)

    args = parser.parse_args()

    if args.command == "list-resumes":
        result = list_candidate_resumes()
    elif args.command == "ensure-folders":
        result = ensure_folders()
    elif args.command == "import-resume":
        result = import_resume(args.file_id)
    elif args.command == "save-draft":
        result = save_draft(args.path, args.name, args.kind, args.mimetype)
    else:
        parser.error("unknown command")
        return

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
