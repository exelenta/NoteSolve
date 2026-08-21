from notesolve.config import Settings


def test_production_settings_parse_network_lists() -> None:
    settings = Settings(
        env="production",
        cors_origins="https://notes.example,https://admin.example",  # type: ignore[arg-type]
        allowed_hosts="notes.example,api",  # type: ignore[arg-type]
    )

    assert settings.is_production is True
    assert settings.cors_origins == ["https://notes.example", "https://admin.example"]
    assert settings.allowed_hosts == ["notes.example", "api"]
