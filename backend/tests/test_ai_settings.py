from app.services.ai_settings_service import decrypt_secret, encrypt_secret, model_from_id


def test_api_key_encryption_round_trip_hides_plaintext():
    secret = "sk-test-value"
    encrypted = encrypt_secret(secret)

    assert encrypted != secret
    assert decrypt_secret(encrypted) == secret


def test_model_capability_tags_are_normalized():
    model = model_from_id("OpenAI", "gpt-4o-mini")

    assert "Mini" in model.capabilities
    assert "Fast" in model.capabilities
    assert model.supports_vision is True
