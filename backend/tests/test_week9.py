import pytest
from pydantic import ValidationError
from sqlalchemy import text

from app.schemas.widget import PublicChatRequest, WidgetSettingsUpdate
from app.utils.crypto import EncryptedString
from app.utils.sanitize import normalize_domain, strip_html, validate_public_https_url


def test_strip_html_removes_tags_and_control_chars():
    assert strip_html("  <script>alert(1)</script>Hello  ") == "alert(1)Hello"
    assert strip_html("plain\x00text") == "plaintext"


def test_normalize_domain():
    assert normalize_domain("HTTPS://Example.COM/path") == "example.com"
    assert normalize_domain("shop.test.com") == "shop.test.com"
    assert normalize_domain("localhost") == "localhost"
    with pytest.raises(ValueError):
        normalize_domain("bad domain")
    with pytest.raises(ValueError):
        normalize_domain("")


def test_validate_public_https_url_allows_public_https():
    assert validate_public_https_url("https://api.wati.io") == "https://api.wati.io"


@pytest.mark.parametrize(
    "url",
    [
        "http://api.wati.io",
        "https://localhost/hook",
        "https://127.0.0.1/hook",
        "https://169.254.169.254/latest/meta-data",
        "https://10.0.0.5/hook",
        "https://192.168.1.10/hook",
        "https://metadata.google.internal/hook",
        "ftp://api.wati.io",
    ],
)
def test_validate_public_https_url_rejects_unsafe(url):
    with pytest.raises(ValueError):
        validate_public_https_url(url)


def test_widget_settings_sanitizes_and_validates():
    payload = WidgetSettingsUpdate(
        title="<b>My shop</b>",
        greeting="<img src=x onerror=alert(1)>Hi",
        allowed_domains=["HTTPS://Shop.Example.com", "localhost"],
    )
    assert payload.title == "My shop"
    assert payload.greeting == "Hi"
    assert payload.allowed_domains == ["shop.example.com", "localhost"]


def test_public_chat_requires_non_empty_message():
    with pytest.raises(ValidationError):
        PublicChatRequest(widget_id="00000000-0000-0000-0000-000000000000", message="")


def test_encrypted_string_roundtrip_and_legacy_plaintext():
    enc = EncryptedString()
    ciphertext = enc.process_bind_param("secret-token", None)
    assert ciphertext != "secret-token"
    assert enc.process_result_value(ciphertext, None) == "secret-token"
    assert enc.process_bind_param(None, None) is None
    assert enc.process_result_value(None, None) is None
    # values written before encryption was enabled are returned unchanged
    assert enc.process_result_value("plain-old-token", None) == "plain-old-token"


@pytest.mark.asyncio
async def test_tokens_encrypted_at_rest(client, db_session):
    import uuid

    email = f"token-enc-{uuid.uuid4().hex[:8]}@test.dev"
    r = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "pass123",
            "company_name": "Token Enc Co",
            "phone": "+21620000000",
        },
    )
    assert r.status_code == 200, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    secret = "tok-secret-123"
    r = await client.put(
        "/api/widget/settings",
        json={"whatsapp_access_token": secret},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    # decrypted transparently on read through the API
    assert r.json()["whatsapp_access_token"] == secret

    # the raw stored value must not be the plaintext token
    raw = (await db_session.execute(
        text("SELECT whatsapp_access_token FROM widget_settings")
    )).scalar_one()
    assert raw != secret
    assert secret not in raw
