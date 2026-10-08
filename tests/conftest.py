def pytest_configure(config):
    """Register custom markers for the test suite."""
    config.addinivalue_line(
        "markers",
        "concept(name): Marker to associate a test with a specific codebase concept ID for traceability.",
    )
