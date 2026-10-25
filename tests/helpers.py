PASSWORD = "S3cure-pass-word"


def post_admin(client, url, data):
    client.get(url)
    response = client.post(
        url,
        {**data, "csrfmiddlewaretoken": client.cookies["csrftoken"].value},
    )
    assert response.status_code == 302, response.content.decode()[:2000]
    return response
