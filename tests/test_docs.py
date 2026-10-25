from rest_framework.test import APIClient


def test_openapi_docs_list_auth_operations():
    client = APIClient()
    schema = client.get(
        "/api/docs/schema/",
        HTTP_ACCEPT="application/vnd.oai.openapi+json",
    )
    assert schema.status_code == 200
    paths = schema.json()["paths"]
    assert "/api/token/" in paths
    assert "/api/token/refresh/" in paths
    assert "/api/token/verify/" in paths
    assert "/api/keys/" in paths
    assert "/api/keys/public/" in paths
    jwks = paths["/api/keys/"]["get"]
    jwks_schema = jwks["responses"]["200"]["content"]["application/json"]["schema"]
    jwks_name = jwks_schema["$ref"].rsplit("/", 1)[-1]
    jwks_fields = schema.json()["components"]["schemas"][jwks_name]["properties"]
    assert "keys" in jwks_fields
    public_key = paths["/api/keys/public/"]["get"]
    public_schema = public_key["responses"]["200"]["content"]["application/json"]["schema"]
    public_name = public_schema["$ref"].rsplit("/", 1)[-1]
    public_fields = schema.json()["components"]["schemas"][public_name]["properties"]
    assert set(public_fields) == {"alg", "public_key"}
    assert "/api/register/" not in paths
    assert "/api/users/" in paths
    created = paths["/api/users/"]["post"]
    response_schema = created["responses"]["201"]["content"]["application/json"]["schema"]
    assert response_schema["$ref"].endswith("/User")
    component = schema.json()["components"]["schemas"]["User"]
    assert set(component["properties"]) == {
        "id",
        "username",
        "email",
        "first_name",
        "last_name",
    }
    request_ref = created["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    request_name = request_ref.rsplit("/", 1)[-1]
    request_fields = schema.json()["components"]["schemas"][request_name]["properties"]
    assert "first_name" in request_fields
    assert "last_name" in request_fields
    assert "password" in request_fields
    assert "password_confirm" not in request_fields

    updated = paths["/api/users/{id}/"]
    assert set(updated) == {"put", "patch"}
    for method in ("put", "patch"):
        operation = updated[method]
        response_ref = operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        assert response_ref.endswith("/User")
        body_ref = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        body_name = body_ref.rsplit("/", 1)[-1]
        body_fields = schema.json()["components"]["schemas"][body_name]["properties"]
        assert set(body_fields) == {"username", "email", "first_name", "last_name"}

    docs = client.get("/api/docs/")
    assert docs.status_code == 200
    body = docs.content.decode()
    assert "swagger-ui" in body
    assert "/api/docs/schema/" in body
