def test_chat_query_property_search(client):
    response = client.post(
        "/api/v1/chat/query",
        json={
            "message": "Show me 3-bedroom homes in Houston under 500000",
            "user_name": "John Doe",
            "user_email": "john@example.com",
            "user_phone": "+1-555-111-2222",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "property_search"
    assert payload["filters_detected"]["city"] == "Houston"
    assert payload["filters_detected"]["bedrooms"] == 3
    assert payload["filters_detected"]["max_price"] == 500000
    assert len(payload["matched_properties"]) == 1
    assert payload["next_step"]["fixed_contact_number"] == "+1-555-123-4567"
    assert payload["next_step"]["recommended_realtor"]["name"] == "Mia Carter"


def test_chat_query_contact_request_without_property_returns_routing(client):
    response = client.post(
        "/api/v1/chat/query",
        json={
            "message": "Who do I contact for this listing?",
            "user_name": "Jane Doe",
            "user_email": "jane@example.com",
            "user_phone": "+1-555-222-3333",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "contact_request"
    assert payload["matched_properties"] == []
    assert payload["next_step"]["recommended_realtor"]["id"] == 1
