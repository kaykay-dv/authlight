# django-authlight

A self-contained Django service that acts as a central authentication provider. It issues JSON Web Tokens (JWTs) that other services can verify with a public key — no shared secret and no callback to this service required.

django-authlight is built for **educational use**: to show how JWT authentication works without standing up a full identity platform such as [Keycloak](https://www.keycloak.org/). The idea is the same — issue a signed token, verify it elsewhere — in a small, readable service.

django-authlight is a standalone service, not a reusable Django app: you install the package, initialize a deployment directory, and run it with the bundled `authlight` command. It is not added to an existing Django project's `INSTALLED_APPS`.

Features:

- User creation and profile updates over a REST API
- JWT access and refresh tokens signed with RS256 (RSA public/private key)
- Public key discovery through an RFC 7517 JWK Set referenced by every token (`jku`/`kid` header), so tools such as [jwt.io](https://jwt.io) can resolve the key automatically
- Interactive OpenAPI documentation at `/api/docs/`
- Django admin at `/console/` with tenant isolation: staff users in the **Tenant admins** group only see the users and groups they created; superusers see everything
- Login lockout with django-axes and separate rate limits for anonymous and authenticated API traffic
- CORS on `/api/*` so a frontend (SPA) on another origin can log in, refresh tokens, and manage users

## Requirements

- Python 3.12 or newer
- pip

## Installation

Install the library directly from [GitHub](https://github.com/kaykay-dv/authlight/):

```bash
pip install "git+https://github.com/kaykay-dv/authlight/"
```

### 1. Initialize a deployment directory

The service reads its configuration from a `.env` file in the **current working directory**, so give it a dedicated directory and run all `authlight` commands from there:

```bash
mkdir authlight-data
cd authlight-data
authlight init
```

`authlight init` creates the following files and applies the database migrations:

| File | Purpose |
| --- | --- |
| `.env` | Configuration with a generated `DJANGO_SECRET_KEY` and local defaults (file permission `600`) |
| `jwt_private.pem` | RSA private key used to sign tokens (file permission `600`). Keep this secret and back it up. |
| `jwt_public.pem` | RSA public key used to verify tokens. Safe to share. |
| `db.sqlite3` | SQLite database (default; see `DATABASE_URL` below) |

Running `authlight init` again leaves an existing `.env` and key pair untouched. `authlight init --force` replaces them — this rotates the secret and the signing key, so existing sessions and tokens will no longer validate.

### 2. Create an administrator and start the server

```bash
authlight createsuperuser
authlight runserver
```

By default the server listens on port 8000. To run it on a different port, pass the port to `runserver` — and use that port in the URLs below instead of `8000`:

```bash
authlight runserver 8080
```

Then open:

| URL | What |
| --- | --- |
| http://127.0.0.1:8000/ | Redirects to the Django admin — the simplest way to log in to the console |
| http://127.0.0.1:8000/console/ | Django admin (sign in with the superuser) |
| http://127.0.0.1:8000/api/docs/ | Interactive OpenAPI documentation |
| http://127.0.0.1:8000/api/docs/schema/ | OpenAPI schema document |

`authlight` accepts any Django management command, e.g. `authlight migrate`, `authlight changepassword <username>`, or `authlight shell`. Always run it from the deployment directory so it finds your `.env` and key files.

## Configuration

Settings are read from `.env` in the working directory (see `.env.example` in the source distribution). Restart the server after changing it.

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django secret. Required when `DJANGO_DEBUG` is false. |
| `DJANGO_DEBUG` | `true` or `false`. When false, secure cookies, HSTS, and HTTPS redirect are enabled. The generated `.env` sets `true` for local use — set it to `false` in production. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts the service responds to. |
| `DATABASE_URL` | Database URL. Defaults to `sqlite:///db.sqlite3` in the working directory. Other databases (e.g. PostgreSQL) need their Python driver installed separately. |
| `JWT_PRIVATE_KEY_FILE` | RSA private key PEM. Default `jwt_private.pem` in the working directory. |
| `JWT_PUBLIC_KEY_FILE` | RSA public key PEM. Default `jwt_public.pem` in the working directory. |
| `JWT_JWKS_URL` | Absolute JWK Set URL written into issued tokens. Empty uses the request host. Set this when the public address differs from the host the request was received on (e.g. behind a proxy). |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | Access token lifetime. Default `5`. |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | Refresh token lifetime. Default `1`. |
| `AXES_FAILURE_LIMIT` | Failed logins before lockout. Default `5`. |
| `AXES_COOLOFF_HOURS` | Lockout duration. Default `1`. |
| `API_THROTTLE_ANON` | Rate for requests without a valid access token, per IP. Default `5/hour`. |
| `API_THROTTLE_USER` | Rate for requests with a valid access token, per user. Default `500/hour`. |
| `API_THROTTLE_USER_CREATE_ANON` | `POST /api/users/` without an access token. Default `5/hour`. |
| `API_THROTTLE_USER_CREATE_USER` | `POST /api/users/` with a valid access token. Default `5/hour`. |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins allowed to call `/api/*` from the browser (SPA login). Default `http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000`. Tokens are sent as `Authorization: Bearer …` — cookies are not used. `GET /api/keys/` always allows any origin so [jwt.io](https://jwt.io) can follow `jku`. |

## API

| Method | Endpoint | Auth | Description |
| --- | --- | --- | --- |
| POST | `/api/users/` | optional | Create a user |
| POST | `/api/token/` | — | Obtain access and refresh tokens |
| POST | `/api/token/refresh/` | refresh token | Get a new access token |
| POST | `/api/token/verify/` | — | Check that a token is valid |
| PUT | `/api/users/{id}/` | access token of user `{id}` | Replace that user's profile |
| PATCH | `/api/users/{id}/` | access token of user `{id}` | Update some profile fields |
| GET | `/api/keys/` | — | RFC 7517 JWK Set containing the public key |
| GET | `/api/keys/public/` | — | Public key as PEM, plus the algorithm |
| GET | `/api/docs/` | — | Interactive OpenAPI documentation |

### Quick start

Create a user (password confirmation is the client's job — there is no `password_confirm` field):

```bash
curl -s -X POST http://127.0.0.1:8000/api/users/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"ada","email":"ada@example.com","first_name":"Ada","last_name":"Lovelace","password":"S3cure-pass-word"}'
```

Obtain tokens:

```bash
curl -s -X POST http://127.0.0.1:8000/api/token/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"ada","password":"S3cure-pass-word"}'
```

Update the user's profile with the access token. `PUT` requires `username`, `email`, `first_name`, and `last_name`; `PATCH` changes only the fields sent. A token may only update its own user id — a missing token returns 401, another user's token returns 403:

```bash
curl -s -X PATCH http://127.0.0.1:8000/api/users/1/ \
  -H 'Authorization: Bearer <access>' \
  -H 'Content-Type: application/json' \
  -d '{"first_name":"Augusta"}'
```

Refresh and verify:

```bash
curl -s -X POST http://127.0.0.1:8000/api/token/refresh/ \
  -H 'Content-Type: application/json' \
  -d '{"refresh":"<refresh>"}'

curl -s -X POST http://127.0.0.1:8000/api/token/verify/ \
  -H 'Content-Type: application/json' \
  -d '{"token":"<access>"}'
```

In the interactive docs at `/api/docs/`, click **Authorize** and paste an access token (without the `Bearer` prefix) to try the authenticated endpoints from the browser.

### Tokens

Access and refresh tokens are signed with RS256. Claims include `user_id` (the primary key as a string), `username`, `email`, and `groups` (group names). Note that existing tokens keep their `username` and `email` claims after a profile update until a new access token is obtained.

Rate limits: requests without a valid access token share the `API_THROTTLE_ANON` limit per IP (this includes the token endpoints), authenticated requests get `API_THROTTLE_USER` per user. `POST /api/users/` has its own pair of limits (`API_THROTTLE_USER_CREATE_ANON` / `API_THROTTLE_USER_CREATE_USER`). Exceeding a limit returns HTTP 429. `/api/docs/` is not rate limited. Counts are kept in Django's default (per-process, in-memory) cache.

django-axes locks `POST /api/token/` and the admin login after `AXES_FAILURE_LIMIT` failed attempts. A locked token request returns HTTP 403:

```json
{"detail": "Too many failed login attempts."}
```

The admin login returns Axes' default HTML lockout response (HTTP 429). A successful login clears the failure count.

## Verify a token in another service

Verifying services only need the public key — never share `jwt_private.pem` or `DJANGO_SECRET_KEY` with them.

Every token header carries `jku` (the JWK Set URL) and `kid` (the key id), so verification can resolve the key automatically. This example uses the [PyJWT](https://pyjwt.readthedocs.io/en/stable/) library — install it in the verifying service first (`pip install PyJWT`). It assumes the auth service runs locally on port 8000, as started above, so you can copy-paste it as-is:

```python
import jwt
from jwt import PyJWKClient

access_token = "..."  # paste an access token from POST /api/token/ here

jwks_client = PyJWKClient("http://localhost:8000/api/keys/")
signing_key = jwks_client.get_signing_key_from_jwt(access_token)

payload = jwt.decode(
    access_token,
    signing_key.key,
    algorithms=["RS256"],
)
user_id = payload["user_id"]
groups = payload["groups"]
print(user_id, groups)
```

Alternatively, fetch the PEM once from `GET /api/keys/public/`, cache it, and pass it to `jwt.decode(...)` with `algorithms=["RS256"]`. Pasting a token into [jwt.io](https://jwt.io) also works: it follows `jku` and selects the key by `kid`. Note that `jku` must be reachable over HTTPS for jwt.io to fetch it; set `JWT_JWKS_URL` if the public URL differs from the request host.

## User administration

The Django admin is at `/console/` (`/admin/` is not served).

`authlight migrate` creates a **Tenant admins** group with add, change, delete, and view permissions on users and groups. That group is not owned by anyone, so only a superuser can assign it.

1. Sign in at `/console/` as the superuser.
2. Create a user, mark them as staff, and add them to **Tenant admins**.
3. Sign in as that user. Users and groups they create are stamped with their account.
4. A second tenant admin does not see those rows, and opening another admin's change page returns 404.

Tenant admin forms cannot set staff status, superuser status, or Django permissions. Groups they create are labels carried in the JWT `groups` claim. Users created through the API have no owner, so only superusers see them in the admin.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `JWT key file not found` | Run `authlight init` in the deployment directory, or `cd` into the directory containing `jwt_private.pem` / `jwt_public.pem` (or set `JWT_PRIVATE_KEY_FILE` / `JWT_PUBLIC_KEY_FILE`). |
| `Set DJANGO_SECRET_KEY when DJANGO_DEBUG is false` | Add `DJANGO_SECRET_KEY` to `.env`, or run `authlight init` to generate one. |
| `DisallowedHost` | Add the host name to `DJANGO_ALLOWED_HOSTS` in `.env`. |
| HTTP 429 on API calls | A rate limit (`API_THROTTLE_*`) was reached; wait or raise it in `.env`. |
| HTTP 403 `Too many failed login attempts` | The account/IP is locked out by django-axes; wait for `AXES_COOLOFF_HOURS` or reset it in the admin/axes records. |
