def test_login_success(client):
    response = client.post("/auth/login", json={"email": "admin@sdr.com", "password": "admin"})
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "fake-token"
    assert body["role"] == "admin"


def test_login_invalid_credentials(client):
    response = client.post("/auth/login", json={"email": "admin@sdr.com", "password": "wrong"})
    assert response.status_code == 401


def test_logout(client, auth_headers):
    response = client.post("/auth/logout", headers=auth_headers)
    assert response.status_code == 204


def test_logout_requires_bearer_token(client):
    response = client.post("/auth/logout")
    assert response.status_code == 401
