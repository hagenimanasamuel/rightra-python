# Rightra for Python

Server-side helpers for Rightra, the digital content protection and rights intelligence product by Oliviuus.

This package does the backend side only: mint short-lived upload tokens, sign S3 and R2 uploads, and call the Rightra API from a Django, Flask, or any Python backend. The browser player is loaded from a script tag on the page. It is not part of this package.

Contact: contact@oliviuus.com

## Requirements

- Python 3.9 or newer
- No runtime dependencies

## Install

    pip install rightra

## Configure

Store these values as environment variables or in your framework settings:

    RIGHTRA_API_KEY=your-rightra-api-key
    RIGHTRA_UPLOAD_SECRET=your-upload-secret
    RIGHTRA_UPLOAD_TOKEN_TTL=900

RIGHTRA_API_KEY is required. Without it every API call fails closed.

## Upload tokens

The PHP upload helper and the Laravel UploadToken::mint both expect a token in the form <expiry>.<hmac>, where hmac = HMAC-SHA256("<contentId>|<expiry>", RIGHTRA_UPLOAD_SECRET) and expiry is a unix timestamp. The Python helper produces exactly the same string.

    import os
    import rightra

    token = rightra.mint_upload_token("RTR-853D-52D0", secret=os.environ["RIGHTRA_UPLOAD_SECRET"])

Send the token to your frontend and let the browser send it as the X-Rightra-Token header when it calls rightra-upload.php. The master secret never reaches the browser.

rightra.verify_upload_token(token, content_id, secret) performs the same check the PHP helper does. Use it if you proxy uploads through your own Python backend instead of the PHP helper.

## API client

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

## Presigned uploads

Sign PUT URLs for S3 or R2 without pulling in boto3.

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

## Errors

Every failure raises rightra.RightraError. The exception carries .status, .code, and .message. Network errors are wrapped in the same type with .status == 0.

## Framework notes

Django and Flask users import the same module. There is no app context and no settings module lookup. Pass configuration explicitly from your own settings layer so secrets stay in one place.

## Limits

This package does not encrypt or decrypt media. It does not render a player. Those are the browser SDK's job. The Python package is the server side of the same workflow.

## License

Proprietary. Copyright OLIVIUUS Ltd. Contact: contact@oliviuus.com