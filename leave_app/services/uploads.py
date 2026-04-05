import os
from datetime import datetime, timezone
from uuid import uuid4

from flask import current_app, redirect, send_from_directory


ALLOWED_OD_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf"}
ALLOWED_OD_MIMETYPES = {"image/png", "image/jpeg", "image/gif", "application/pdf"}
IMAGE_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
}


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def configure_uploads(app):
    project_root = os.path.abspath(os.path.join(app.root_path, os.pardir))
    upload_root = app.config.get("LOCAL_UPLOAD_ROOT") or os.path.join(project_root, "uploads")
    os.makedirs(upload_root, exist_ok=True)

    if app.config["STORAGE_BACKEND"] == "local":
        upload_folder = os.path.join(upload_root, app.config["OD_UPLOAD_PREFIX"])
        leave_upload_folder = os.path.join(upload_root, app.config["LEAVE_UPLOAD_PREFIX"])
        os.makedirs(upload_folder, exist_ok=True)
        os.makedirs(leave_upload_folder, exist_ok=True)
        app.config["OD_UPLOAD_FOLDER"] = upload_folder
        app.config["LEAVE_UPLOAD_FOLDER"] = leave_upload_folder


def storage_key(prefix, filename):
    base_prefix = current_app.config.get("STORAGE_PREFIX", "").strip("/")
    parts = [part for part in (base_prefix, prefix.strip("/"), filename) if part]
    return "/".join(parts)


def storage_backend():
    return current_app.config.get("STORAGE_BACKEND", "local")


def object_storage_enabled():
    return storage_backend() in {"s3", "oci"}


def build_object_storage_client_kwargs():
    client_kwargs = {
        "service_name": "s3",
        "region_name": current_app.config.get("STORAGE_REGION"),
    }

    endpoint_url = current_app.config.get("STORAGE_ENDPOINT_URL")
    if endpoint_url:
        client_kwargs["endpoint_url"] = endpoint_url

    access_key_id = current_app.config.get("STORAGE_ACCESS_KEY_ID")
    secret_access_key = current_app.config.get("STORAGE_SECRET_ACCESS_KEY")
    if access_key_id and secret_access_key:
        client_kwargs["aws_access_key_id"] = access_key_id
        client_kwargs["aws_secret_access_key"] = secret_access_key

    try:
        from botocore.config import Config as BotoConfig
    except ImportError:
        BotoConfig = None

    if BotoConfig is not None:
        client_kwargs["config"] = BotoConfig(
            signature_version="s3v4",
            s3={"addressing_style": current_app.config.get("STORAGE_ADDRESSING_STYLE", "auto")},
        )
    return client_kwargs


def object_storage_client():
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 must be installed when using object storage backends.") from exc

    return boto3.client(**build_object_storage_client_kwargs())


def allowed_od_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_OD_EXTENSIONS


def sniff_upload_mimetype(file_storage):
    header = file_storage.stream.read(16)
    file_storage.stream.seek(0)

    if header.startswith(b"%PDF"):
        return "application/pdf"

    for signature, mimetype in IMAGE_SIGNATURES.items():
        if header.startswith(signature):
            return mimetype

    return None


def validate_uploaded_proof(file_storage):
    if not file_storage or not file_storage.filename:
        return None, None, "Proof file is missing."

    if not allowed_od_file(file_storage.filename):
        return None, None, "Only PNG, JPG, GIF, and PDF files are allowed."

    detected_mimetype = sniff_upload_mimetype(file_storage)
    if detected_mimetype not in ALLOWED_OD_MIMETYPES:
        return None, None, "Uploaded proof does not match an allowed file type."

    extension = file_storage.filename.rsplit(".", 1)[1].lower()
    safe_filename = f"{utcnow().strftime('%Y%m%d%H%M%S')}_{uuid4().hex}.{extension}"
    return safe_filename, detected_mimetype, None


def validate_uploaded_document(file_storage):
    return validate_uploaded_proof(file_storage)


def save_uploaded_file(file_storage, prefix, filename, mimetype):
    if object_storage_enabled():
        client = object_storage_client()
        key = storage_key(prefix, filename)
        file_storage.stream.seek(0)
        client.upload_fileobj(
            file_storage.stream,
            current_app.config["STORAGE_BUCKET"],
            key,
            ExtraArgs={"ContentType": mimetype},
        )
        return

    folder_config_key = "OD_UPLOAD_FOLDER" if prefix == current_app.config["OD_UPLOAD_PREFIX"] else "LEAVE_UPLOAD_FOLDER"
    file_storage.save(os.path.join(current_app.config[folder_config_key], filename))


def uploaded_file_exists(prefix, filename):
    if object_storage_enabled():
        client = object_storage_client()
        try:
            client.head_object(Bucket=current_app.config["STORAGE_BUCKET"], Key=storage_key(prefix, filename))
            return True
        except Exception:
            return False

    folder_config_key = "OD_UPLOAD_FOLDER" if prefix == current_app.config["OD_UPLOAD_PREFIX"] else "LEAVE_UPLOAD_FOLDER"
    return os.path.exists(os.path.join(current_app.config[folder_config_key], filename))


def build_file_response(prefix, filename, mimetype):
    if object_storage_enabled():
        client = object_storage_client()
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": current_app.config["STORAGE_BUCKET"], "Key": storage_key(prefix, filename)},
            ExpiresIn=current_app.config["STORAGE_PRESIGNED_URL_EXPIRY"],
        )
        return redirect(url)

    folder_config_key = "OD_UPLOAD_FOLDER" if prefix == current_app.config["OD_UPLOAD_PREFIX"] else "LEAVE_UPLOAD_FOLDER"
    return send_from_directory(
        current_app.config[folder_config_key],
        filename,
        as_attachment=False,
        mimetype=mimetype,
    )
