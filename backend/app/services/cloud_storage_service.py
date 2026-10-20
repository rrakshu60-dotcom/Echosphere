"""
EchoSphere Cloud Storage Service (Hugging Face Datasets Git LFS CDN Engine)
==========================================================================
Provides 100% free, unlimited, permanent cloud storage backed by Hugging Face Datasets
and Cloudflare Global Edge CDN for:
  1. Synthesized Neural Audio Streams (WAV / MP3) for ESP32 Corridor Speakers & Web Clients.
  2. Institutional Circular Attachments (PDFs, Images, Scanned Documents).

Features:
  - Permanent public raw CDN URLs:
      https://huggingface.co/datasets/{repo_id}/resolve/main/{path_in_repo}
  - ESP32 & Mobile streaming without requiring authorization headers or signed tokens.
  - Render Container Reboot Resilience: Re-fetches wiped assets from Hugging Face Git LFS.
  - Graceful Fallback: Operates seamlessly on local static disk if offline or token is unset.
"""

import os
import io
import json
import logging
import threading
from typing import Optional, Dict, Any, Union
from dotenv import load_dotenv

# Automatically load environment variables from backend/.env or workspace root .env
backend_env = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
if os.path.exists(backend_env):
    load_dotenv(backend_env)
else:
    load_dotenv()

logger = logging.getLogger("echosphere.cloud_storage")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
MANIFEST_PATH = os.path.join(STATIC_DIR, ".storage_manifest.json")


class CloudStorageService:
    """Unified cloud & local storage manager powered by Hugging Face Git LFS Datasets."""

    _lock = threading.Lock()
    _api = None
    _repo_id: Optional[str] = None
    _token: Optional[str] = None
    _cloud_enabled: Optional[bool] = None
    _manifest: Dict[str, str] = {}
    _manifest_loaded: bool = False

    @classmethod
    def _load_manifest(cls) -> None:
        """Loads cached mapping of filenames to public CDN URLs."""
        if cls._manifest_loaded:
            return
        with cls._lock:
            if cls._manifest_loaded:
                return
            if os.path.exists(MANIFEST_PATH):
                try:
                    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                        cls._manifest = json.load(f)
                except Exception as e:
                    logger.debug(f"Could not load storage manifest: {e}")
                    cls._manifest = {}
            cls._manifest_loaded = True

    @classmethod
    def _save_manifest(cls) -> None:
        """Persists the manifest to disk safely."""
        try:
            os.makedirs(STATIC_DIR, exist_ok=True)
            with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
                json.dump(cls._manifest, f, indent=2)
        except Exception as e:
            logger.debug(f"Could not persist storage manifest: {e}")

    @classmethod
    def _init_client(cls) -> bool:
        """Initializes Hugging Face API client and validates or creates the dataset repository."""
        if cls._cloud_enabled is not None:
            return cls._cloud_enabled

        cls._load_manifest()

        token = (
            os.getenv("HF_TOKEN")
            or os.getenv("HUGGINGFACE_TOKEN")
            or os.getenv("HUGGING_FACE_HUB_TOKEN")
            or ""
        ).strip()

        if not token:
            logger.info("[Storage] HF_TOKEN not set. Running in resilient local static storage mode.")
            cls._cloud_enabled = False
            return False

        try:
            from huggingface_hub import HfApi

            api = HfApi(token=token)
            # Verify credentials
            user_info = api.whoami()
            username = user_info.get("name") or "echosphere"
            configured_repo = (os.getenv("HF_DATASET_REPO") or "").strip()

            if configured_repo:
                repo_id = configured_repo
            else:
                repo_id = f"{username}/echosphere-assets"

            # Ensure dataset repository exists and is public for direct CDN access
            try:
                api.repo_info(repo_id=repo_id, repo_type="dataset")
            except Exception:
                logger.info(f"[Storage] Dataset repository '{repo_id}' not found. Auto-creating public repository...")
                try:
                    api.create_repo(repo_id=repo_id, repo_type="dataset", private=False, exist_ok=True)
                    logger.info(f"[Storage] Successfully created public dataset repository: {repo_id}")
                except Exception as create_err:
                    logger.warning(f"[Storage] Could not auto-create dataset repo '{repo_id}': {create_err}")

            cls._api = api
            cls._token = token
            cls._repo_id = repo_id
            cls._cloud_enabled = True
            logger.info(f"[Storage] Hugging Face Datasets CDN active on repo: {repo_id}")
            return True

        except Exception as e:
            logger.warning(f"[Storage] Hugging Face authentication/init warning: {e}. Falling back to local static storage.")
            cls._cloud_enabled = False
            return False

    @classmethod
    def is_cloud_enabled(cls) -> bool:
        """Returns True if Hugging Face Datasets cloud storage is operational."""
        return cls._init_client()

    @classmethod
    def get_public_url(cls, folder: str, filename: str) -> str:
        """
        Returns the permanent public URL for an asset.
        If Cloud CDN is enabled or file is in manifest, returns the Cloudflare raw CDN URL.
        Otherwise returns the local `/static/{folder}/{filename}` path.
        """
        cls._load_manifest()
        key = f"{folder}/{filename}"
        if key in cls._manifest:
            return cls._manifest[key]

        if cls.is_cloud_enabled() and cls._repo_id:
            cdn_url = f"https://huggingface.co/datasets/{cls._repo_id}/resolve/main/{folder}/{filename}"
            return cdn_url

        return f"/static/{folder}/{filename}"

    @classmethod
    def upload_file(
        cls,
        local_path: str,
        folder: str = "audio_streams",
        custom_filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Uploads a local file to Hugging Face Datasets CDN and records the permanent raw URL.
        Falls back seamlessly to local static disk if offline or unauthenticated.
        """
        cls._load_manifest()
        filename = custom_filename or os.path.basename(local_path)
        path_in_repo = f"{folder}/{filename}"
        local_url = f"/static/{folder}/{filename}"

        # Check manifest cache
        if path_in_repo in cls._manifest:
            return {
                "status": "cached",
                "public_url": cls._manifest[path_in_repo],
                "cdn_url": cls._manifest[path_in_repo],
                "local_url": local_url,
                "file_name": filename,
                "path_in_repo": path_in_repo,
                "storage_mode": "huggingface_cdn",
            }

        # Check if Hugging Face cloud is available
        if cls.is_cloud_enabled() and cls._api and cls._repo_id and os.path.exists(local_path):
            try:
                commit_msg = f"Add {folder} asset: {filename}"
                cls._api.upload_file(
                    path_or_fileobj=local_path,
                    path_in_repo=path_in_repo,
                    repo_id=cls._repo_id,
                    repo_type="dataset",
                    commit_message=commit_msg,
                )
                cdn_url = f"https://huggingface.co/datasets/{cls._repo_id}/resolve/main/{path_in_repo}"
                with cls._lock:
                    cls._manifest[path_in_repo] = cdn_url
                    cls._save_manifest()

                logger.info(f"[Storage] Successfully uploaded to HF CDN: {cdn_url}")
                return {
                    "status": "uploaded",
                    "public_url": cdn_url,
                    "cdn_url": cdn_url,
                    "local_url": local_url,
                    "file_name": filename,
                    "path_in_repo": path_in_repo,
                    "storage_mode": "huggingface_cdn",
                }
            except Exception as e:
                logger.warning(f"[Storage] Upload to Hugging Face failed: {e}. Preserving local static asset.")

        # Local static fallback
        dest_dir = os.path.join(STATIC_DIR, folder)
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, filename)

        if os.path.abspath(local_path) != os.path.abspath(dest_path) and os.path.exists(local_path):
            try:
                import shutil
                shutil.copy2(local_path, dest_path)
            except Exception:
                pass

        return {
            "status": "local",
            "public_url": local_url,
            "cdn_url": None,
            "local_url": local_url,
            "file_name": filename,
            "path_in_repo": path_in_repo,
            "storage_mode": "local_static",
        }

    @classmethod
    def upload_bytes(
        cls,
        data: bytes,
        filename: str,
        folder: str = "attachments",
    ) -> Dict[str, Any]:
        """
        Saves raw bytes (such as uploaded PDFs, images, or audio) and publishes to CDN.
        """
        cls._load_manifest()
        dest_dir = os.path.join(STATIC_DIR, folder)
        os.makedirs(dest_dir, exist_ok=True)
        local_path = os.path.join(dest_dir, filename)

        # Write locally first for instant local access
        try:
            with open(local_path, "wb") as f:
                f.write(data)
        except Exception as e:
            logger.warning(f"[Storage] Could not write local cache file {local_path}: {e}")

        path_in_repo = f"{folder}/{filename}"
        local_url = f"/static/{folder}/{filename}"

        if cls.is_cloud_enabled() and cls._api and cls._repo_id:
            try:
                file_obj = io.BytesIO(data)
                cls._api.upload_file(
                    path_or_fileobj=file_obj,
                    path_in_repo=path_in_repo,
                    repo_id=cls._repo_id,
                    repo_type="dataset",
                    commit_message=f"Upload attachment: {filename}",
                )
                cdn_url = f"https://huggingface.co/datasets/{cls._repo_id}/resolve/main/{path_in_repo}"
                with cls._lock:
                    cls._manifest[path_in_repo] = cdn_url
                    cls._save_manifest()

                logger.info(f"[Storage] Uploaded bytes to HF CDN: {cdn_url}")
                return {
                    "status": "uploaded",
                    "public_url": cdn_url,
                    "cdn_url": cdn_url,
                    "local_url": local_url,
                    "file_name": filename,
                    "path_in_repo": path_in_repo,
                    "storage_mode": "huggingface_cdn",
                }
            except Exception as e:
                logger.warning(f"[Storage] Cloud upload error for {filename}: {e}")

        return {
            "status": "local",
            "public_url": local_url,
            "cdn_url": None,
            "local_url": local_url,
            "file_name": filename,
            "path_in_repo": path_in_repo,
            "storage_mode": "local_static",
        }

    @classmethod
    def restore_file_from_cdn_if_missing(
        cls,
        filename: str,
        folder: str = "audio_streams",
    ) -> Optional[str]:
        """
        Render Ephemeral Storage Resurrector:
        If a local file was wiped during container sleep or redeployment,
        fetches it back from the Hugging Face Git LFS dataset repository.
        Returns the restored local file path, or None if unavailable.
        Strictly requires the file to be tracked in the storage manifest to eliminate
        wasteful 1.8s CDN probes on freshly synthesized or non-existent files.
        """
        dest_dir = os.path.join(STATIC_DIR, folder)
        local_path = os.path.join(dest_dir, filename)

        if os.path.exists(local_path) and os.path.getsize(local_path) > 512:
            return local_path

        path_in_repo = f"{folder}/{filename}"
        cls._load_manifest()

        # Strictly verify file is recorded in manifest before attempting network request
        cdn_url = cls._manifest.get(path_in_repo)
        if not cdn_url:
            return None

        try:
            import requests
            logger.info(f"[Storage] Restoring missing container file from CDN: {cdn_url}")
            resp = requests.get(cdn_url, timeout=3.0)
            if resp.status_code == 200 and len(resp.content) > 512:
                os.makedirs(dest_dir, exist_ok=True)
                with open(local_path, "wb") as f:
                    f.write(resp.content)
                logger.info(f"[Storage] Successfully restored {filename} to local container storage ({len(resp.content)} bytes).")
                return local_path
        except Exception as e:
            logger.debug(f"[Storage] Could not restore {filename} from CDN: {e}")

        return None
