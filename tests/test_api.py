from backend.app.tools import search_listings


def login_admin(client):
    response = client.post("/admin/login", json={"username": "admin", "password": "secret-pass"})
    assert response.status_code == 200


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["listing_source_mode"] == "demo_json"
    assert payload["assistant_brand"] == "Test Concierge"
    assert payload["brokerage_name"] == "Test Brokerage"


def test_create_conversation_and_history(client):
    create_response = client.post("/conversations")
    assert create_response.status_code == 201
    conversation_id = create_response.json()["conversation_id"]

    history_response = client.get(f"/conversations/{conversation_id}/history")
    assert history_response.status_code == 200
    assert history_response.json()["messages"] == []


def test_message_returns_listing_results_and_handoff(client):
    conversation_id = client.post("/conversations").json()["conversation_id"]
    response = client.post(
        f"/conversations/{conversation_id}/messages",
        json={"message": "Find 3-bedroom homes in Houston under 500000 and connect me to a realtor"},
    )
    payload = response.json()
    assert response.status_code == 200
    assert payload["listing_results"]
    assert payload["handoff"]["fixed_contact_number"] == "+1-800-TEST"
    assert payload["handoff"]["recommended_realtor"]["name"]
    assert any(source["type"] == "listing_source" for source in payload["sources"])
    assert payload["data_status"] == "demo"


def test_stream_endpoint_emits_chunks_and_meta(client):
    conversation_id = client.post("/conversations").json()["conversation_id"]
    response = client.post(
        f"/conversations/{conversation_id}/messages/stream",
        json={"message": "Tell me about prop-017"},
    )
    assert response.status_code == 200
    text = response.text
    assert '"chunk"' in text
    assert '"meta"' in text
    assert '"done": true' in text


def test_handoff_precedence_listing_then_city_then_fallback(client):
    listing_match = client.post("/handoff", json={"listing_id": "prop-017"}).json()
    assert listing_match["recommended_realtor"]["id"] == "realtor-008"
    assert listing_match["reason"] == "Matched by listing specialist assignment"

    city_match = client.post("/handoff", json={"city": "Austin"}).json()
    assert city_match["recommended_realtor"]["cities_covered"] == ["Austin"]

    fallback = client.post("/handoff", json={"city": "Unknown City"}).json()
    assert fallback["recommended_realtor"]["id"] == "realtor-001"
    assert fallback["reason"] == "Default brokerage fallback realtor"


def test_conversation_history_persists_assistant_metadata(client):
    conversation_id = client.post("/conversations").json()["conversation_id"]
    client.post(
        f"/conversations/{conversation_id}/messages",
        json={"message": "What should I know before renting in Austin?"},
    )
    history = client.get(f"/conversations/{conversation_id}/history").json()["messages"]
    assert len(history) == 2
    assistant_message = history[-1]
    assert assistant_message["role"] == "assistant"
    assert assistant_message["sources"]
    assert assistant_message["data_status"] == "demo"


def test_listing_search_tool_filters_by_city_and_bedrooms():
    results = search_listings(city="Houston", bedrooms=3, max_price=500000, listing_type="sale")
    assert results
    assert all(item["city"] == "Houston" for item in results)
    assert all(item["bedrooms"] >= 3 for item in results)


def test_settings_requires_admin_session(client):
    response = client.get("/settings")
    assert response.status_code == 401

    schema_response = client.get("/settings/schema")
    assert schema_response.status_code == 401


def test_settings_spa_route_serves_html(client):
    response = client.get("/settings", headers={"accept": "text/html"})
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_settings_update_masks_secret_and_applies_runtime_config(client):
    login_admin(client)

    response = client.put(
        "/settings",
        json={
            "values": {
                "BROKERAGE_NAME": "Configured Realty",
                "BROKERAGE_CONTACT_NUMBER": "+1-800-CONFIG",
                "LISTING_SOURCE_MODE": "har_mls",
                "OPENAI_API_KEY": "sk-test-value",
            }
        },
    )
    assert response.status_code == 200
    payload = response.json()
    values = {item["key"]: item for item in payload["values"]}

    assert values["BROKERAGE_NAME"]["value"] == "Configured Realty"
    assert values["OPENAI_API_KEY"]["value"] == "Configured"
    assert values["OPENAI_API_KEY"]["is_set"] is True

    health = client.get("/health").json()
    assert health["brokerage_name"] == "Configured Realty"
    assert health["listing_source_mode"] == "har_mls"

    handoff = client.post("/handoff", json={"city": "Austin"}).json()
    assert handoff["fixed_contact_number"] == "+1-800-CONFIG"


def test_admin_session_and_logout(client):
    login_admin(client)
    session_response = client.get("/admin/session")
    assert session_response.status_code == 200
    assert session_response.json()["authenticated"] is True

    logout_response = client.post("/admin/logout")
    assert logout_response.status_code == 200
    assert logout_response.json()["authenticated"] is False


def test_seeded_demo_conversations_load_with_sources_and_handoff(seeded_client):
    conversations = seeded_client.get("/conversations").json()["conversations"]
    assert len(conversations) == 4
    assert conversations[0]["title"] == "Seller prep and brokerage handoff"

    history = seeded_client.get("/conversations/demo-conv-houston-buyer/history").json()["messages"]
    assert len(history) == 6

    assistant_message = history[-1]
    assert assistant_message["sources"]
    assert assistant_message["sources"][0]["url"] == "https://www.reso.org/reso-web-api/"
    assert assistant_message["handoff"]["fixed_contact_number"] == "+1-800-TEST"
    assert assistant_message["handoff"]["recommended_realtor"]["brokerage"] == "Test Brokerage"


def test_demo_seeding_is_idempotent_and_uses_runtime_placeholders(seeded_client):
    database_module = __import__("backend.app.database", fromlist=["init_db"])
    database_module.init_db()

    conversations = seeded_client.get("/conversations").json()["conversations"]
    assert len(conversations) == 4

    history = seeded_client.get("/conversations/demo-conv-seller-handoff/history").json()["messages"]
    assistant_message = history[-1]
    assert assistant_message["handoff"]["fixed_contact_number"] == "+1-800-TEST"
    assert assistant_message["handoff"]["recommended_realtor"]["brokerage"] == "Test Brokerage"
