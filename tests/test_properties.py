def test_property_filtering_by_city_bedrooms_and_price(client):
    response = client.get(
        "/api/v1/properties",
        params={"city": "Houston", "bedrooms": 3, "max_price": 500000, "status": "for_sale"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["city"] == "Houston"
    assert payload[0]["bedrooms"] == 3
    assert payload[0]["price"] == 450000.0


def test_property_detail_not_found(client):
    response = client.get("/api/v1/properties/999")
    assert response.status_code == 404
