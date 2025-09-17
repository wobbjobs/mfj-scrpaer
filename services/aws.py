import boto3
from botocore.exceptions import BotoCoreError, ClientError
from config.settings import AWS_S3_BUCKET_NAME, AWS_S3_REGION,AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
from pathlib import Path
from datetime import datetime
import os

BASE_DIR = Path(__file__).resolve().parent.parent
LOCAL_DOWNLOADS_DIR = BASE_DIR / "tmp"


def ensure_local_directory(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_or_create_job_folder(job_title: str) -> Path:
    clean = "".join(c for c in job_title if c.isalnum() or c in (" ", "_", "-")).rstrip()
    return ensure_local_directory(LOCAL_DOWNLOADS_DIR / clean)


def get_or_create_section_folder(section_name: str, parent_folder_path: str | Path) -> Path:
    return ensure_local_directory(Path(parent_folder_path) / section_name)


def ensure_local_directory(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_or_create_job_folder(job_title: str) -> Path:
    clean = "".join(c for c in job_title if c.isalnum() or c in (" ", "_", "-")).rstrip()
    return ensure_local_directory(LOCAL_DOWNLOADS_DIR / clean)


def get_or_create_section_folder(section_name: str, parent_folder_path: str | Path) -> Path:
    return ensure_local_directory(Path(parent_folder_path) / section_name)


class S3Services:
    def __init__(
        self,
        client=None,
        region: str | None = None,
        bucket_name: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
    ):
        self.s3 = client or boto3.client(
            "s3",
            region_name=region or AWS_S3_REGION,
            aws_access_key_id=access_key_id or AWS_ACCESS_KEY_ID,
            aws_secret_access_key=secret_access_key or AWS_SECRET_ACCESS_KEY,
        )
        self.bucket_name = bucket_name or AWS_S3_BUCKET_NAME

    def upload_to_s3(self, file_name: str | Path, bucket: str | None = None, object_name: str | None = None) -> bool:
        key = object_name or Path(file_name).name
        self.s3.upload_file(str(file_name), bucket or self.bucket_name, key)
        return True

    def upload_job_files_to_s3(self, job_title: str, bucket_name: str | None = None) -> dict:
        bucket = bucket_name or self.bucket_name
        today = datetime.now().strftime("%Y-%m-%d")
        clean_job_title = "".join(c for c in job_title if c.isalnum() or c in (" ", "_", "-")).rstrip()
        local_job_folder = LOCAL_DOWNLOADS_DIR / clean_job_title

        results = {
            "job_title": job_title,
            "date": today,
            "uploaded_files": [],
            "total_uploaded": 0,
            "total_failed": 0,
        }

        if not local_job_folder.exists():
            return results

        applicants_folder = local_job_folder / "applicants"
        if applicants_folder.exists():
            uploaded = self._upload_section_files(
                applicants_folder,
                f"{today}/{clean_job_title}/applicants/",
                bucket,
            )
            results["uploaded_files"].extend(uploaded)
            results["total_uploaded"] += len(uploaded)

        possible_matches_folder = local_job_folder / "possible_matches"
        if possible_matches_folder.exists():
            uploaded = self._upload_section_files(
                possible_matches_folder,
                f"{today}/{clean_job_title}/possible_matches/",
                bucket,
            )
            results["uploaded_files"].extend(uploaded)
            results["total_uploaded"] += len(uploaded)

        return results

    def _upload_section_files(self, local_folder: Path, s3_prefix: str, bucket: str) -> list[dict]:
        uploaded: list[dict] = []
        for file_path in local_folder.glob("*.pdf"):
            s3_key = f"{s3_prefix}{file_path.name}"
            self.s3.upload_file(str(file_path), bucket, s3_key)
            uploaded.append(
                {"local_path": str(file_path), "s3_key": s3_key, "file_name": file_path.name}
            )
        return uploaded

    def upload_all_tmp_files_to_s3(self, bucket_name: str | None = None) -> list[dict]:
        bucket = bucket_name or self.bucket_name
        all_results: list[dict] = []
        if not LOCAL_DOWNLOADS_DIR.exists():
            return all_results
        for job_folder in LOCAL_DOWNLOADS_DIR.iterdir():
            if job_folder.is_dir():
                result = self.upload_job_files_to_s3(job_folder.name, bucket)
                all_results.append(result)
        return all_results

    def retrieve_s3_url(self, object_name: str, bucket: str | None = None, expiration: int = 3600) -> str | None:
        try:
            url = self.s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket or self.bucket_name, "Key": object_name},
                ExpiresIn=expiration,
            )
            return url
        except (BotoCoreError, ClientError) as e:
            print(f"Error generating presigned URL: {e}")
            return None