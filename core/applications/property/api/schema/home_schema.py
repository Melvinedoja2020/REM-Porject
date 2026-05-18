from drf_spectacular.utils import OpenApiExample
from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import extend_schema_view

from core.applications.property.api.serializers import HomePageSerializer

HomePageViewSchema = extend_schema_view(
    list=extend_schema(
        tags=["Properties"],
        summary="Home Page Aggregated Data",
        description="""
Returns a single aggregated payload for the application home page.

This endpoint is designed to reduce frontend network calls by combining:

- Featured properties
- Property categories

Use cases:
- Mobile app home screen
- Web landing page
- Initial property discovery experience

Authentication:
- Public endpoint (no auth required)

Performance note:
- Optimized for single-call rendering
        """,
        responses=HomePageSerializer,
        examples=[
            OpenApiExample(
                "Home Page Response Example",
                value={
                    "featured_properties": [
                        {
                            "id": "uuid",
                            "title": "Luxury 4 Bedroom Duplex",
                            "price": 50000000,
                            "location": "Lekki, Lagos",
                        }
                    ],
                    "categories": [
                        {
                            "id": "uuid",
                            "name": "Apartments",
                            "slug": "apartments",
                        }
                    ],
                },
                response_only=True,
            )
        ],
    )
)
