from tests.conftest import extract_csrf_token


def test_lead_routing_requires_authentication(client):
    response = client.post(
        "/api/v1/leads/route",
        json={
            "user_name": "John Doe",
            "user_email": "john@example.com",
            "user_phone": "+1-555-111-2222",
            "user_question": "I want to buy a condo in Houston",
            "desired_city": "Houston",
            "desired_budget": 450000,
            "property_id": 2,
        },
    )

    assert response.status_code == 401


def test_lead_routing_prefers_property_realtor(authenticated_client):
    response = authenticated_client.post(
        "/api/v1/leads/route",
        json={
            "user_name": "John Doe",
            "user_email": "john@example.com",
            "user_phone": "+1-555-111-2222",
            "user_question": "I want to buy a condo in Houston",
            "desired_city": "Houston",
            "desired_budget": 450000,
            "property_id": 2,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assigned_realtor"]["id"] == 1
    assert payload["routing_reason"] == "Matched by property realtor_id"


def test_settings_update_changes_fallback_routing(authenticated_client):
    settings_page = authenticated_client.get("/dashboard/settings")
    csrf_token = extract_csrf_token(settings_page.text)

    save_response = authenticated_client.post(
        "/dashboard/settings",
        data={
            "csrf_token": csrf_token,
            "fixed_contact_number": "+1-555-999-0000",
            "default_realtor_id": "2",
            "chat_result_limit": "4",
            "default_desired_city_fallback": "",
            "dashboard_density": "compact",
            "dashboard_table_page_size": "10",
            "feature_integrations_panel": "on",
            "feature_lead_routing_writes": "on",
            "feature_catalog_visibility": "on",
        },
        follow_redirects=False,
    )

    assert save_response.status_code == 303

    route_response = authenticated_client.post(
        "/api/v1/leads/route",
        json={
            "user_name": "Sam Taylor",
            "user_email": "sam@example.com",
            "user_phone": "+1-555-777-8888",
            "user_question": "I need help exploring homes in El Paso",
            "desired_city": "El Paso",
            "desired_budget": 350000,
            "property_id": None,
        },
    )

    assert route_response.status_code == 200
    payload = route_response.json()
    assert payload["fixed_contact_number"] == "+1-555-999-0000"
    assert payload["assigned_realtor"]["id"] == 2
    assert payload["routing_reason"] == "Assigned default realtor"


def test_csrf_is_required_for_settings_update(authenticated_client):
    response = authenticated_client.post(
        "/dashboard/settings",
        data={
            "fixed_contact_number": "+1-555-000-0000",
            "default_realtor_id": "1",
            "chat_result_limit": "5",
            "default_desired_city_fallback": "",
            "dashboard_density": "comfortable",
            "dashboard_table_page_size": "10",
        },
    )

    assert response.status_code == 403


def test_lead_routing_toggle_can_block_writes(authenticated_client):
    settings_page = authenticated_client.get("/dashboard/settings")
    csrf_token = extract_csrf_token(settings_page.text)

    authenticated_client.post(
        "/dashboard/settings",
        data={
            "csrf_token": csrf_token,
            "fixed_contact_number": "+1-555-123-4567",
            "default_realtor_id": "1",
            "chat_result_limit": "5",
            "default_desired_city_fallback": "",
            "dashboard_density": "comfortable",
            "dashboard_table_page_size": "10",
            "feature_integrations_panel": "on",
            "feature_catalog_visibility": "on",
        },
        follow_redirects=False,
    )

    response = authenticated_client.post(
        "/api/v1/leads/route",
        json={
            "user_name": "Blocked User",
            "user_email": "blocked@example.com",
            "user_phone": "+1-555-888-9999",
            "user_question": "I want to buy in Houston",
            "desired_city": "Houston",
            "desired_budget": 500000,
            "property_id": None,
        },
    )

    assert response.status_code == 403
