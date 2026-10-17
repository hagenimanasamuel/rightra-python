# Rightra for Python

Server-side helpers for [Rightra](https://oliviuus.com) by Oliviuus.

This package covers the backend only. It mints short-lived upload tokens, signs S3 and R2 uploads, and calls the Rightra API from Django, Flask, or any other Python backend. The browser player is loaded separately with a script tag and is not part of this package.

## Requirements

- Python 3.9 or newer
- No runtime dependencies

## Installation

```bash
pip install rightra
```

## Configuration

Keep these values in environment variables or in your framework's settings:

```bash
RIGHTRA_API_KEY=your-rightra-api-key
RIGHTRA_UPLOAD_SECRET=your-upload-secret
RIGHTRA_UPLOAD_TOKEN_TTL=900
```

`RIGHTRA_API_KEY` is required. Without it, every API call fails closed.

`RIGHTRA_UPLOAD_TOKEN_TTL` is the token lifetime in seconds.

The package does not read your environment or settings on its own. Read the values in your application and pass them in explicitly, so secrets stay in one place.

## Upload tokens

Upload tokens have the form `<expiry>.<hmac>`:

- `expiry` is a Unix timestamp.
- `hmac` is `HMAC-SHA256("<contentId>|<expiry>", RIGHTRA_UPLOAD_SECRET)`.

This is the same format the PHP upload helper and Laravel's `UploadToken::mint` use, and the Python helper produces an identical string.

```python
import os
import rightra

token = rightra.mint_upload_token(
    "RTR-853D-52D0",
    secret=os.environ["RIGHTRA_UPLOAD_SECRET"],
)
```

Send the token to your frontend. The browser then passes it in the `X-Rightra-Token` header when it calls `rightra-upload.php`. The upload secret never reaches the browser.

### Verifying tokens

```python
rightra.verify_upload_token(token, content_id, secret)
```

This performs the same check as the PHP helper. Use it if you proxy uploads through your own Python backend instead of using the PHP helper.

## API client

```python
import os
from rightra import Client

client = Client(api_key=os.environ["RIGHTRA_API_KEY"])

created = client.register_content(
    title="My Film",
    type="film",
    description="Feature length film.",
    creator_name="Example Studio",
)

content_id = created["content"]["content_id"]

client.set_manifest(
    content_id,
    manifest_url="https://your-storage.example/manifest.json",
)

session = client.create_playback_session(
    content_id,
    viewer_id=str(request.user.id),
    viewer_label=request.user.get_full_name(),
    territory="RW",
)
```

`viewer_id` can be any stable identifier from your own system.

## Presigned uploads

Sign PUT URLs for S3 or R2 without installing boto3.

```python
import os
from rightra import sign_s3_put, sign_r2_put

put_url = sign_s3_put(
    access_key=os.environ["AWS_ACCESS_KEY_ID"],
    secret_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    bucket="my-rightra-bucket",
    key=f"uploads/{content_id}/seg-0.enc",
    region="us-east-1",
)

r2_url = sign_r2_put(
    account_id=os.environ["R2_ACCOUNT_ID"],
    access_key=os.environ["R2_ACCESS_KEY_ID"],
    secret_key=os.environ["R2_SECRET_ACCESS_KEY"],
    bucket="rightra",
    key=f"uploads/{content_id}/seg-0.enc",
)
```

## Error handling

All failures raise `rightra.RightraError`, which exposes three attributes:

| Attribute | Description |
| --- | --- |
| `status` | HTTP status code. `0` for network errors. |
| `code` | Error code returned by the API. |
| `message` | Human-readable description. |

```python
from rightra import RightraError

try:
    client.set_manifest(content_id, manifest_url=url)
except RightraError as e:
    log.error("Rightra request failed: %s (%s, status %s)", e.message, e.code, e.status)
```

## Framework notes

Django and Flask use the same module. There is no app context and no settings lookup, so pass configuration from your own settings layer.

## License

Proprietary. Copyright OLIVIUUS Ltd.