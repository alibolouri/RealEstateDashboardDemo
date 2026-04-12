from tests.conftest import extract_csrf_token


def test_dashboard_requires_login(client):
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard/login"


def test_dashboard_login_and_security_headers(client):
    response = client.get("/dashboard/login")

    assert response.status_code == 200
    assert "Admin Login" in response.text
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "Content-Security-Policy" in response.headers


def test_dashboard_login_rejects_invalid_credentials(client):
    login_page = client.get("/dashboard/login")
    csrf_token = extract_csrf_token(login_page.text)

    response = client.post(
        "/dashboard/login",
        data={
            "username": "admin",
            "password": "wrong-password",
            "csrf_token": csrf_token,
            "next_path": "/dashboard",
        },
    )

    assert response.status_code == 401
    assert "Invalid admin credentials." in response.text


def test_integrations_catalog_and_masked_secret_render(authenticated_client):
    page = authenticated_client.get("/dashboard/integrations")
    assert page.status_code == 200
    assert "HubSpot CRM Contacts" in page.text
    assert '{"' not in page.text

    detail_page = authenticated_client.get("/dashboard/integrations/7")
    csrf_token = extract_csrf_token(detail_page.text)

    save_response = authenticated_client.post(
        "/dashboard/integrations/7",
        data={
            "csrf_token": csrf_token,
            "enabled": "on",
            "account_sid": "AC123456",
            "auth_token": "super-secret-value",
            "from_number": "+1-555-444-5555",
            "notes": "<script>alert('x')</script> Twilio staging connector",
        },
        follow_redirects=True,
    )

    assert save_response.status_code == 200
    assert "super-secret-value" not in save_response.text
    assert "&lt;script&gt;alert" in save_response.text
    assert "<script>alert" not in save_response.text
    assert "Saved securely in demo storage" in save_response.text


def test_dashboard_pages_render_structured_content_without_json(authenticated_client):
    properties_page = authenticated_client.get("/dashboard/properties")
    leads_page = authenticated_client.get("/dashboard/leads")
    realtors_page = authenticated_client.get("/dashboard/realtors")

    assert properties_page.status_code == 200
    assert leads_page.status_code == 200
    assert realtors_page.status_code == 200
    assert '{"' not in properties_page.text
    assert '{"' not in leads_page.text
    assert '{"' not in realtors_page.text
