from core.helpers.enums import SubscriptionPlan
from django.core.exceptions import ValidationError


FEATURE_LIMITS = {
    SubscriptionPlan.FREE: {
        "properties": None,  # free users can only list 1 property
        "featured_listings": None,  # cannot feature properties
    },
    SubscriptionPlan.BASIC: {
        "properties": None,
        "featured_listings": None,
    },
    SubscriptionPlan.PREMIUM: {
        "properties": None,
        "featured_listings": None,
    },
    SubscriptionPlan.ENTERPRISE: {
        "properties": None,  # unlimited
        "featured_listings": None,  # unlimited
    },
}
