"""
Enhanced API documentation system for LMS microservices
"""
import json
from typing import Dict, List, Any, Optional, Callable
from fastapi import FastAPI, Request, Response
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from shared.common.logging import get_logger
from shared.common.versioning import version_manager
from shared.common.monitoring import metrics_collector

logger = get_logger("common-docs")


class EnhancedAPIDocs:
    """Enhanced API documentation generator"""

    def __init__(self, app: Optional[FastAPI], title: str = "LMS API", version: str = "1.0.0"):
        self.app = app
        self.title = title
        self.version = version
        self.custom_schemas: Dict[str, Dict[str, Any]] = {}
        self.examples: Dict[str, Dict[str, Any]] = {}
        self.security_schemes: Dict[str, Dict[str, Any]] = {}
        self.tags_metadata: List[Dict[str, Any]] = []

    def add_custom_schema(self, name: str, schema: Dict[str, Any]):
        """Add custom schema definition"""
        self.custom_schemas[name] = schema

    def add_example(self, operation_id: str, example: Dict[str, Any]):
        """Add example for operation"""
        self.examples[operation_id] = example

    def add_security_scheme(self, name: str, scheme: Dict[str, Any]):
        """Add security scheme"""
        self.security_schemes[name] = scheme

    def add_tag_metadata(self, name: str, description: str, external_docs: Optional[Dict[str, Any]] = None):
        """Add tag metadata"""
        tag: Dict[str, Any] = {"name": name, "description": description}
        if external_docs:
            tag["externalDocs"] = external_docs
        self.tags_metadata.append(tag)

    def generate_openapi_schema(self) -> Dict[str, Any]:
        """Generate enhanced OpenAPI schema"""
        # Get base OpenAPI schema
        routes = self.app.routes if self.app else []
        openapi_schema = get_openapi(
            title=self.title,
            version=self.version,
            openapi_version="3.0.2",
            description=self._get_description(),
            routes=routes,
            tags=self.tags_metadata
        )

        # Enhance with custom components
        if "components" not in openapi_schema:
            openapi_schema["components"] = {}

        # Add custom schemas
        if self.custom_schemas:
            if "schemas" not in openapi_schema["components"]:
                openapi_schema["components"]["schemas"] = {}
            openapi_schema["components"]["schemas"].update(self.custom_schemas)

        # Add security schemes
        if self.security_schemes:
            if "securitySchemes" not in openapi_schema["components"]:
                openapi_schema["components"]["securitySchemes"] = {}
            openapi_schema["components"]["securitySchemes"].update(self.security_schemes)

        # Add examples to operations
        self._add_examples_to_operations(openapi_schema)

        # Add version information
        openapi_schema["info"]["x-api-versions"] = version_manager.list_versions()

        # Add server information
        openapi_schema["servers"] = self._get_servers()

        return openapi_schema

    def _get_description(self) -> str:
        """Get API description"""
        return """
        # LMS (Learning Management System) API

        A comprehensive, scalable, and production-ready Learning Management System built with modern technologies and enterprise-grade architecture.

        ## Features

        - **AI-Powered Course Generation**: Generate courses with detailed lessons and assessments
        - **User Management**: Complete user profiles, progress tracking, and achievements
        - **Assessment System**: Assignments, quizzes, and AI-powered grading
        - **Analytics**: Learning analytics and performance insights
        - **Real-time Notifications**: WebSocket-based notifications
        - **File Management**: Secure file upload and storage

        ## Authentication

        This API uses JWT (JSON Web Tokens) for authentication. Include the token in the Authorization header:

        ```
        Authorization: Bearer <your-jwt-token>
        ```

        ## Rate Limiting

        API endpoints are rate limited. Check the response headers for current limits:
        - `X-RateLimit-Limit`: Maximum requests allowed
        - `X-RateLimit-Remaining`: Remaining requests
        - `X-RateLimit-Reset`: Time when limit resets

        ## Versioning

        This API supports versioning. Use the appropriate version prefix or header:
        - URL Path: `/v1/endpoint`
        - Header: `X-API-Version: v1`

        ## Error Handling

        The API uses consistent error response formats. All errors include:
        - `error_code`: Machine-readable error code
        - `message`: Human-readable error message
        - `details`: Additional error details (optional)
        """

    def _add_examples_to_operations(self, openapi_schema: Dict[str, Any]):
        """Add examples to operation responses"""
        if "paths" not in openapi_schema:
            return

        for path, path_item in openapi_schema["paths"].items():
            for method, operation in path_item.items():
                if method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    continue

                operation_id = operation.get("operationId", "")
                if operation_id in self.examples:
                    example = self.examples[operation_id]

                    # Add response examples
                    if "responses" in operation:
                        for status_code, response in operation["responses"].items():
                            if "content" in response:
                                for content_type, content in response["content"].items():
                                    if "examples" not in content:
                                        content["examples"] = {}
                                    content["examples"]["default"] = example

    def _get_servers(self) -> List[Dict[str, Any]]:
        """Get server configurations"""
        return [
            {
                "url": "http://localhost:8000",
                "description": "Development server"
            },
            {
                "url": "https://api.lms.com",
                "description": "Production server"
            },
            {
                "url": "https://staging-api.lms.com",
                "description": "Staging server"
            }
        ]

    def get_swagger_ui_html(self, request: Request) -> Any:
        """Get enhanced Swagger UI HTML"""
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title=f"{self.title} - Swagger UI",
            oauth2_redirect_url="/docs/oauth2-redirect",
            swagger_js_url="/static/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger-ui.css",
            init_oauth=None,
            swagger_ui_parameters={
                "docExpansion": "none",
                "filter": True,
                "showExtensions": True,
                "showCommonExtensions": True,
                "syntaxHighlight": {
                    "activate": True,
                    "theme": "arta"
                },
                "tryItOutEnabled": True,
                "requestInterceptor": """
                    function(request) {
                        // Add auth token if available
                        const token = localStorage.getItem('jwt_token');
                        if (token) {
                            request.headers.Authorization = 'Bearer ' + token;
                        }
                        return request;
                    }
                """,
                "responseInterceptor": """
                    function(response) {
                        // Log responses for debugging
                        console.log('API Response:', response);
                        return response;
                    }
                """
            }
        )

    def get_redoc_html(self, request: Request) -> Any:
        """Get ReDoc HTML"""
        return get_redoc_html(
            openapi_url="/openapi.json",
            title=f"{self.title} - ReDoc",
            redoc_js_url="/static/redoc.standalone.js"
        )


# Global documentation instance
api_docs = EnhancedAPIDocs(None)


def setup_api_documentation(app: FastAPI, service_name: str = "LMS API"):
    """Setup enhanced API documentation for a service"""
    global api_docs
    api_docs = EnhancedAPIDocs(app, title=service_name)

    # Add common security schemes
    api_docs.add_security_scheme(
        "bearerAuth",
        {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT Authorization header using the Bearer scheme. Example: 'Authorization: Bearer {token}'"
        }
    )

    api_docs.add_security_scheme(
        "apiKeyAuth",
        {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API Key for service-to-service authentication"
        }
    )

    # Add common tag metadata
    api_docs.add_tag_metadata(
        "auth",
        "Authentication and authorization endpoints",
        {"url": "/docs/auth", "description": "Authentication documentation"}
    )

    api_docs.add_tag_metadata(
        "users",
        "User management and profiles",
        {"url": "/docs/users", "description": "User management documentation"}
    )

    api_docs.add_tag_metadata(
        "courses",
        "Course management and content",
        {"url": "/docs/courses", "description": "Course management documentation"}
    )

    api_docs.add_tag_metadata(
        "ai",
        "AI-powered features and content generation",
        {"url": "/docs/ai", "description": "AI features documentation"}
    )

    api_docs.add_tag_metadata(
        "analytics",
        "Learning analytics and reporting",
        {"url": "/docs/analytics", "description": "Analytics documentation"}
    )

    # Add common response schemas
    api_docs.add_custom_schema(
        "ErrorResponse",
        {
            "type": "object",
            "properties": {
                "error_code": {"type": "string", "example": "VALIDATION_ERROR"},
                "message": {"type": "string", "example": "Validation failed"},
                "details": {"type": "object", "nullable": True},
                "timestamp": {"type": "string", "format": "date-time"},
                "request_id": {"type": "string"}
            },
            "required": ["error_code", "message", "timestamp"]
        }
    )

    api_docs.add_custom_schema(
        "SuccessResponse",
        {
            "type": "object",
            "properties": {
                "success": {"type": "boolean", "example": True},
                "data": {"type": "object"},
                "message": {"type": "string", "example": "Operation successful"},
                "timestamp": {"type": "string", "format": "date-time"},
                "request_id": {"type": "string"}
            },
            "required": ["success", "timestamp"]
        }
    )

    api_docs.add_custom_schema(
        "PaginatedResponse",
        {
            "type": "object",
            "properties": {
                "items": {"type": "array", "items": {"type": "object"}},
                "total": {"type": "integer", "example": 100},
                "page": {"type": "integer", "example": 1},
                "page_size": {"type": "integer", "example": 20},
                "total_pages": {"type": "integer", "example": 5},
                "has_next": {"type": "boolean", "example": True},
                "has_prev": {"type": "boolean", "example": False}
            },
            "required": ["items", "total", "page", "page_size", "total_pages"]
        }
    )

    # Register documentation routes
    @app.get("/openapi.json", include_in_schema=False)
    async def get_openapi_json():
        """Get OpenAPI JSON schema"""
        return api_docs.generate_openapi_schema()

    @app.get("/docs", include_in_schema=False)
    async def get_swagger_ui(request: Request):
        """Get Swagger UI"""
        return Response(
            content=api_docs.get_swagger_ui_html(request),
            media_type="text/html"
        )

    @app.get("/redoc", include_in_schema=False)
    async def get_redoc(request: Request):
        """Get ReDoc"""
        return Response(
            content=api_docs.get_redoc_html(request),
            media_type="text/html"
        )

    @app.get("/docs/health", include_in_schema=False)
    async def docs_health():
        """Documentation health check"""
        return {
            "status": "healthy",
            "service": "api-documentation",
            "version": api_docs.version,
            "endpoints": {
                "swagger_ui": "/docs",
                "redoc": "/redoc",
                "openapi_json": "/openapi.json"
            }
        }

    logger.info(f"Enhanced API documentation setup for {service_name}")


# Documentation decorators
def document_operation(
    summary: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    deprecated: bool = False,
    operation_id: Optional[str] = None
):
    """Decorator to add documentation to operations"""
    def decorator(func: Callable) -> Callable:
        if summary:
            func.__doc__ = summary
        if description:
            if not hasattr(func, '_docs_description'):
                func._docs_description = description
        if tags:
            func._docs_tags = tags
        if deprecated:
            func._docs_deprecated = deprecated
        if operation_id:
            func._docs_operation_id = operation_id
        return func
    return decorator


def add_response_example(operation_id: str, status_code: int, example: Dict[str, Any]):
    """Add response example for operation"""
    if operation_id not in api_docs.examples:
        api_docs.examples[operation_id] = {}

    api_docs.examples[operation_id][str(status_code)] = example


def add_request_example(operation_id: str, example: Dict[str, Any]):
    """Add request example for operation"""
    if operation_id not in api_docs.examples:
        api_docs.examples[operation_id] = {}

    api_docs.examples[operation_id]["request"] = example


# API documentation middleware
async def docs_middleware(request: Request, call_next):
    """Middleware to enhance API documentation"""
    # Add request tracking for docs
    request.state.start_time = request.state.start_time if hasattr(request.state, 'start_time') else None

    response = await call_next(request)

    # Add documentation headers
    if request.url.path.startswith("/docs") or request.url.path == "/openapi.json":
        response.headers["X-API-Docs"] = "enhanced"
        response.headers["X-API-Version"] = api_docs.version

    return response


# Documentation generation utilities
def generate_service_docs(service_name: str, endpoints: List[Dict[str, Any]]) -> str:
    """Generate markdown documentation for service"""
    docs = f"# {service_name} API Documentation\n\n"

    docs += "## Overview\n\n"
    docs += f"This document describes the API endpoints for the {service_name}.\n\n"

    docs += "## Authentication\n\n"
    docs += "All endpoints require authentication unless otherwise specified.\n\n"

    docs += "## Endpoints\n\n"

    for endpoint in endpoints:
        docs += f"### {endpoint['method']} {endpoint['path']}\n\n"
        if 'summary' in endpoint:
            docs += f"**{endpoint['summary']}**\n\n"
        if 'description' in endpoint:
            docs += f"{endpoint['description']}\n\n"
        if 'parameters' in endpoint:
            docs += "**Parameters:**\n\n"
            for param in endpoint['parameters']:
                docs += f"- `{param['name']}` ({param['type']}): {param.get('description', '')}\n"
            docs += "\n"
        if 'responses' in endpoint:
            docs += "**Responses:**\n\n"
            for status, resp in endpoint['responses'].items():
                docs += f"- `{status}`: {resp.get('description', '')}\n"
            docs += "\n"
        docs += "---\n\n"

    return docs


def export_api_docs(format: str = "json") -> str:
    """Export API documentation in specified format"""
    schema = api_docs.generate_openapi_schema()

    if format == "json":
        return json.dumps(schema, indent=2)
    elif format == "yaml":
        try:
            import yaml
            return yaml.dump(schema, default_flow_style=False)
        except ImportError:
            return json.dumps(schema, indent=2)
    else:
        return json.dumps(schema, indent=2)


# Documentation metrics
async def get_docs_metrics() -> Dict[str, Any]:
    """Get documentation usage metrics"""
    await metrics_collector.increment_counter("docs_accessed")

    return {
        "total_endpoints": len(api_docs.app.routes) if api_docs.app else 0,
        "custom_schemas": len(api_docs.custom_schemas),
        "security_schemes": len(api_docs.security_schemes),
        "examples": len(api_docs.examples),
        "tags": len(api_docs.tags_metadata)
    }