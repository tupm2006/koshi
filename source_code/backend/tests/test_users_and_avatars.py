import io
import pytest
from fastapi.testclient import TestClient
from app.services.uploads import get_upload_path, get_upload_dir

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00"
    b"\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\xff\xd9"

WEBP_BYTES = b"RIFF\x1a\x00\x00\x00WEBPVP8 \x0e\x00\x00\x000\x01\x00\x9d\x01*\x01\x00\x01\x00\x00"

def test_user_self_profile_patch(client: TestClient, member_auth_headers: dict):
    me = client.get("/api/auth/me", headers=member_auth_headers).json()
    my_id = me["id"]

    # 1. Self update full_name and skills
    patch_res = client.patch(
        f"/api/users/{my_id}",
        json={"full_name": "Updated Dev Name", "skills": "python,vue,fastapi"},
        headers=member_auth_headers
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["full_name"] == "Updated Dev Name"
    assert data["skills"] == "python,vue,fastapi"

    # 2. Cannot update role via patch
    patch_role_res = client.patch(
        f"/api/users/{my_id}",
        json={"role": "PM"},
        headers=member_auth_headers
    )
    assert patch_role_res.status_code == 200
    assert patch_role_res.json()["role"] == "MEMBER"

def test_user_cannot_patch_another_profile(client: TestClient, pm_auth_headers: dict, member_auth_headers: dict):
    pm = client.get("/api/auth/me", headers=pm_auth_headers).json()
    pm_id = pm["id"]

    # Member tries to patch PM profile -> 403 Forbidden
    res = client.patch(
        f"/api/users/{pm_id}",
        json={"full_name": "Hacked Name"},
        headers=member_auth_headers
    )
    assert res.status_code == 403

def test_avatar_upload_and_download_flow(client: TestClient, member_auth_headers: dict):
    me = client.get("/api/auth/me", headers=member_auth_headers).json()
    my_id = me["id"]

    # 1. Upload valid PNG avatar
    upload_res = client.post(
        "/api/users/me/avatar",
        files={"file": ("profile.png", io.BytesIO(PNG_BYTES), "image/png")},
        headers=member_auth_headers
    )
    assert upload_res.status_code == 200
    user_data = upload_res.json()
    assert user_data["avatar_file"] is not None
    assert user_data["avatar_file"].endswith(".png")
    first_avatar_file = user_data["avatar_file"]
    expected_url_prefix = f"/api/users/{my_id}/avatar?v="
    assert user_data["avatar_url"].startswith(expected_url_prefix)

    # Verify file exists on disk
    file_path = get_upload_path(first_avatar_file)
    assert file_path.exists()

    # 2. Download avatar via GET /api/users/{user_id}/avatar
    download_res = client.get(f"/api/users/{my_id}/avatar")
    assert download_res.status_code == 200
    assert download_res.headers["Content-Type"] == "image/png"
    assert download_res.headers["X-Content-Type-Options"] == "nosniff"
    assert "private" in download_res.headers["Cache-Control"]
    assert "max-age=86400" in download_res.headers["Cache-Control"]
    assert download_res.content == PNG_BYTES

    # 3. Upload new avatar (JPEG) and verify old file is unlinked
    upload2_res = client.post(
        "/api/users/me/avatar",
        files={"file": ("profile.jpg", io.BytesIO(JPEG_BYTES), "image/jpeg")},
        headers=member_auth_headers
    )
    assert upload2_res.status_code == 200
    second_avatar_file = upload2_res.json()["avatar_file"]
    assert second_avatar_file != first_avatar_file
    assert second_avatar_file.endswith(".jpg")

    # Old avatar must be deleted from disk
    assert not file_path.exists()
    assert get_upload_path(second_avatar_file).exists()

    # Clean up second file
    get_upload_path(second_avatar_file).unlink(missing_ok=True)

def test_avatar_upload_rejects_invalid_mime_and_magic_bytes(client: TestClient, member_auth_headers: dict):
    # 1. Invalid MIME type (text/plain)
    res_mime = client.post(
        "/api/users/me/avatar",
        files={"file": ("malicious.txt", io.BytesIO(b"hello world"), "text/plain")},
        headers=member_auth_headers
    )
    assert res_mime.status_code == 400

    # 2. Fake PNG (MIME is image/png but content is text)
    res_fake_png = client.post(
        "/api/users/me/avatar",
        files={"file": ("fake.png", io.BytesIO(b"plain text pretending to be png 1234567890"), "image/png")},
        headers=member_auth_headers
    )
    assert res_fake_png.status_code == 400

def test_avatar_upload_rejects_oversized_file(client: TestClient, member_auth_headers: dict):
    # Oversized payload (> 2MB) with valid PNG header
    oversized = PNG_BYTES + (b"A" * (2 * 1024 * 1024 + 1024))
    res_oversized = client.post(
        "/api/users/me/avatar",
        files={"file": ("huge.png", io.BytesIO(oversized), "image/png")},
        headers=member_auth_headers
    )
    assert res_oversized.status_code == 413
