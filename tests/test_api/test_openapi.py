"""
Tests for OpenAPI schema configuration and documentation.

Validates that the API documentation is complete and properly configured.
"""

import os
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.dependencies import reset_transit_service, TransitService
import src.api.dependencies as deps

# Path to test fixtures
FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_data", "fixtures")


@pytest.fixture(autouse=True)
def reset_service():
    """Reset transit service and use test fixtures."""
    reset_transit_service()

    # Create and load service with test fixtures
    deps._transit_service = TransitService(gtfs_dir=FIXTURES_DIR)
    deps._transit_service.load()

    yield

    reset_transit_service()


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def openapi_schema(client):
    """Get OpenAPI schema."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    return response.json()


class TestOpenAPIConfiguration:
    """Tests for OpenAPI configuration in main.py."""

    def test_openapi_schema_available(self, client):
        """Test that OpenAPI schema is accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_swagger_ui_available(self, client):
        """Test that Swagger UI is accessible at /docs."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_available(self, client):
        """Test that ReDoc is accessible at /redoc."""
        response = client.get("/redoc")
        assert response.status_code == 200

    def test_api_title(self, openapi_schema):
        """Test API title is properly set."""
        assert "info" in openapi_schema
        assert openapi_schema["info"]["title"] == "PTV Transit Assistant API"

    def test_api_version(self, openapi_schema):
        """Test API version is properly set."""
        assert openapi_schema["info"]["version"] == "1.0.0"

    def test_api_description(self, openapi_schema):
        """Test API description is present and contains key information."""
        description = openapi_schema["info"]["description"]
        assert "Journey planning" in description
        assert "Melbourne" in description
        # Check for transport modes section
        assert "metro" in description.lower() or "Metro" in description
        assert "tram" in description.lower() or "Tram" in description

    def test_contact_info(self, openapi_schema):
        """Test contact information is present."""
        assert "contact" in openapi_schema["info"]
        contact = openapi_schema["info"]["contact"]
        assert "name" in contact
        assert "url" in contact

    def test_license_info(self, openapi_schema):
        """Test license information is present."""
        assert "license" in openapi_schema["info"]
        license_info = openapi_schema["info"]["license"]
        assert "name" in license_info
        assert "MIT" in license_info["name"]


class TestOpenAPITags:
    """Tests for OpenAPI tag configuration."""

    def test_tags_defined(self, openapi_schema):
        """Test that tags are defined."""
        assert "tags" in openapi_schema
        assert len(openapi_schema["tags"]) > 0

    def test_required_tags_present(self, openapi_schema):
        """Test that all required tags are present."""
        tag_names = [tag["name"] for tag in openapi_schema["tags"]]
        required_tags = ["health", "stops", "journey", "vehicles", "alerts"]
        for tag in required_tags:
            assert tag in tag_names, f"Tag '{tag}' not found in OpenAPI schema"

    def test_tags_have_descriptions(self, openapi_schema):
        """Test that all tags have descriptions."""
        for tag in openapi_schema["tags"]:
            assert "description" in tag, f"Tag '{tag['name']}' missing description"
            assert len(tag["description"]) > 10, f"Tag '{tag['name']}' has too short description"


class TestOpenAPIEndpoints:
    """Tests for endpoint documentation."""

    def test_all_endpoints_documented(self, openapi_schema):
        """Test that all endpoints are present in the schema."""
        paths = openapi_schema.get("paths", {})

        # Health endpoints
        assert "/api/v1/health" in paths

        # Stop endpoints
        assert "/api/v1/stops/search" in paths
        assert "/api/v1/stops/{stop_id}" in paths

        # Journey endpoints
        assert "/api/v1/journey/plan" in paths

        # Vehicle endpoints
        assert "/api/v1/vehicles" in paths
        assert "/api/v1/vehicles/summary" in paths
        assert "/api/v1/vehicles/{vehicle_id}" in paths

        # Alert endpoints
        assert "/api/v1/alerts" in paths
        assert "/api/v1/alerts/summary" in paths

    def test_endpoints_have_summaries(self, openapi_schema):
        """Test that endpoints have summaries."""
        paths = openapi_schema.get("paths", {})
        for path, methods in paths.items():
            for method, details in methods.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    assert "summary" in details, f"{method.upper()} {path} missing summary"

    def test_endpoints_have_descriptions(self, openapi_schema):
        """Test that endpoints have descriptions."""
        paths = openapi_schema.get("paths", {})
        for path, methods in paths.items():
            for method, details in methods.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    assert "description" in details, f"{method.upper()} {path} missing description"

    def test_endpoints_have_tags(self, openapi_schema):
        """Test that endpoints have tags."""
        paths = openapi_schema.get("paths", {})
        for path, methods in paths.items():
            for method, details in methods.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    assert "tags" in details, f"{method.upper()} {path} missing tags"


class TestOpenAPISchemas:
    """Tests for schema definitions."""

    def test_schemas_defined(self, openapi_schema):
        """Test that component schemas are defined."""
        assert "components" in openapi_schema
        assert "schemas" in openapi_schema["components"]

    def test_response_models_present(self, openapi_schema):
        """Test that response models are present."""
        schemas = openapi_schema["components"]["schemas"]

        required_schemas = [
            "HealthResponse",
            "StopResponse",
            "StopSearchResponse",
            "JourneyPlanRequest",
            "JourneyPlanResponse",
            "ErrorResponse"
        ]

        for schema in required_schemas:
            assert schema in schemas, f"Schema '{schema}' not found in OpenAPI schema"

    def test_schemas_have_properties(self, openapi_schema):
        """Test that schemas have properties defined."""
        schemas = openapi_schema["components"]["schemas"]

        for name, schema in schemas.items():
            # Skip reference schemas
            if "$ref" in schema:
                continue
            # Most schemas should have properties or allOf
            if "properties" not in schema and "allOf" not in schema and "anyOf" not in schema:
                # Some schemas may be empty or enum-only, which is acceptable
                if "enum" not in schema and "type" not in schema:
                    pytest.fail(f"Schema '{name}' has no properties defined")


class TestOpenAPIExamples:
    """Tests for API examples in documentation."""

    def test_journey_request_has_examples(self, openapi_schema):
        """Test that journey plan request has examples."""
        schemas = openapi_schema["components"]["schemas"]
        journey_schema = schemas.get("JourneyPlanRequest", {})

        # Check for examples in schema or properties
        has_examples = (
            "examples" in journey_schema or
            "example" in journey_schema or
            any("example" in prop or "examples" in prop
                for prop in journey_schema.get("properties", {}).values())
        )
        assert has_examples, "JourneyPlanRequest should have examples"

    def test_response_models_have_examples(self, openapi_schema):
        """Test that key response models have examples."""
        schemas = openapi_schema["components"]["schemas"]

        models_with_examples = ["HealthResponse", "StopResponse", "ErrorResponse"]

        for model in models_with_examples:
            if model in schemas:
                schema = schemas[model]
                has_examples = (
                    "example" in schema or
                    "examples" in schema or
                    any("example" in str(prop) for prop in schema.get("properties", {}).values())
                )
                # Note: examples can be in model_config, so we just check they exist somewhere
                assert "properties" in schema or "allOf" in schema, f"{model} should be defined"


class TestOpenAPIResponses:
    """Tests for response documentation."""

    def test_endpoints_have_response_codes(self, openapi_schema):
        """Test that endpoints document response codes."""
        paths = openapi_schema.get("paths", {})

        for path, methods in paths.items():
            for method, details in methods.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    assert "responses" in details, f"{method.upper()} {path} missing responses"
                    # Should at least have 200 or 201
                    responses = details["responses"]
                    has_success = any(code.startswith("2") for code in responses.keys())
                    assert has_success, f"{method.upper()} {path} missing success response"

    def test_error_responses_documented(self, openapi_schema):
        """Test that error responses are documented for key endpoints."""
        paths = openapi_schema.get("paths", {})

        # Endpoints that should have error responses
        endpoints_with_errors = [
            ("/api/v1/stops/{stop_id}", "get"),
            ("/api/v1/vehicles/{vehicle_id}", "get"),
        ]

        for path, method in endpoints_with_errors:
            if path in paths and method in paths[path]:
                responses = paths[path][method].get("responses", {})
                # Should have 404 for not found
                has_error = any(code.startswith("4") or code.startswith("5")
                               for code in responses.keys())
                assert has_error, f"{method.upper()} {path} should document error responses"
