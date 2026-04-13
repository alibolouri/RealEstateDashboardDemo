from backend.app.tools import search_listings


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
