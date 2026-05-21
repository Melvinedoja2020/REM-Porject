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

Designed to eliminate multiple round-trips by combining everything the
home screen needs into one response:

**featured_properties**
Up to 6 active featured listings in card shape, ordered by featured
listing start date. Each card includes price display, agent summary,
main image URL, and the `is_featured` / `is_favorited` flags.
`is_favorited` reflects the authenticated user's state — unauthenticated
requests always receive `false`.

**categories**
One entry per listing type (For Sale, For Rent, Short Let) with a live
property count, icon identifier, and short description for the
Browse by Category cards.

**search_config**
Static configuration for the hero search form dropdowns. Contains:
- `listing_types` — options for the Type dropdown
- `price_ranges` — price band options keyed by listing type value,
  so the frontend can swap bands when the Type selection changes.
  Each band includes `price_min` and `price_max` values ready to
  attach directly to the property listing query params.

**Authentication:** Public — no token required.

**Performance:** 5–6 SQL statements regardless of result size.
(1 featured query + 3 prefetches + 1 GROUP BY + 1 optional subquery
for authenticated favorite annotation.)
        """,
        responses={200: HomePageSerializer},
        examples=[
            OpenApiExample(
                "Home Page Response",
                summary="Full home page payload",
                value={
                    "featured_properties": [
                        {
                            "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                            "title": "Luxury Modern Villa",
                            "slug": "luxury-modern-villa",
                            "location": "Banana Island, Lagos",
                            "price": "75000000.00",
                            "price_display": "₦75,000,000",
                            "price_suffix": "",
                            "property_type": "House",
                            "property_type_display": "House",
                            "property_listing": "for_sale",
                            "listing_type_display": "For Sale",
                            "bedrooms": 5,
                            "bathrooms": 4,
                            "sqft": 4200,
                            "is_available": True,
                            "availability_label": "Available",
                            "is_featured": True,
                            "is_favorited": False,
                            "main_image_url": "https://example.com/media/properties/villa.jpg",
                            "agent": {
                                "id": "7cb4a123-9abc-4def-8123-4d5e6f7a8b9c",
                                "full_name": "Emeka Okafor",
                                "avatar_url": "https://example.com/media/agents/emeka.jpg",
                                "phone": "+2348012345678",
                                "email": "emeka@realty.com",
                                "total_listings": 14,
                            },
                            "created_at": "2025-01-15T10:30:00Z",
                        }
                    ],
                    "categories": [
                        {
                            "listing_type": "for_sale",
                            "label": "For Sale",
                            "icon": "home",
                            "description": "Browse properties available for sale across Africa.",
                            "count": 142,
                        },
                        {
                            "listing_type": "rent",
                            "label": "For Rent",
                            "icon": "key",
                            "description": "Find short and long-term rental properties for you.",
                            "count": 89,
                        },
                        {
                            "listing_type": "short_let",
                            "label": "Short Let",
                            "icon": "calendar",
                            "description": "Discover flexible short-let accommodation near you.",
                            "count": 34,
                        },
                    ],
                    "search_config": {
                        "listing_types": [
                            {"value": "for_sale",  "label": "For Sale"},
                            {"value": "rent",      "label": "For Rent"},
                            {"value": "short_let", "label": "Short Let"},
                        ],
                        "price_ranges": {
                            "for_sale": [
                                {"label": "Any price",                    "price_min": None, "price_max": None},
                                {"label": "Under ₦10,000,000",            "price_min": None, "price_max": "10000000.00"},
                                {"label": "₦10,000,000 – ₦30,000,000",   "price_min": "10000000.00",  "price_max": "30000000.00"},
                                {"label": "₦30,000,000 – ₦50,000,000",   "price_min": "30000000.00",  "price_max": "50000000.00"},
                                {"label": "₦50,000,000 – ₦100,000,000",  "price_min": "50000000.00",  "price_max": "100000000.00"},
                                {"label": "₦100,000,000 – ₦200,000,000", "price_min": "100000000.00", "price_max": "200000000.00"},
                                {"label": "Above ₦200,000,000",           "price_min": "200000000.00", "price_max": None},
                            ],
                            "rent": [
                                {"label": "Any price",              "price_min": None,          "price_max": None},
                                {"label": "Under ₦100,000/month",   "price_min": None,          "price_max": "100000.00"},
                                {"label": "Under ₦200,000/month",   "price_min": None,          "price_max": "200000.00"},
                                {"label": "Under ₦500,000/month",   "price_min": None,          "price_max": "500000.00"},
                                {"label": "Under ₦1,000,000/month", "price_min": None,          "price_max": "1000000.00"},
                                {"label": "Above ₦1,000,000/month", "price_min": "1000000.00",  "price_max": None},
                            ],
                            "short_let": [
                                {"label": "Any price",            "price_min": None,        "price_max": None},
                                {"label": "Under ₦50,000/night",  "price_min": None,        "price_max": "50000.00"},
                                {"label": "Under ₦100,000/night", "price_min": None,        "price_max": "100000.00"},
                                {"label": "Under ₦200,000/night", "price_min": None,        "price_max": "200000.00"},
                                {"label": "Under ₦500,000/night", "price_min": None,        "price_max": "500000.00"},
                                {"label": "Above ₦500,000/night", "price_min": "500000.00", "price_max": None},
                            ],
                        },
                    },
                },
                response_only=True,
                status_codes=["200"],
            )
        ],
    )
)
