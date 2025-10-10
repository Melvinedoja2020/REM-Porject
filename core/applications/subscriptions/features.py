from core.helper.enums import SubscriptionPlan
from django.core.exceptions import ValidationError


FEATURE_LIMITS = {
    SubscriptionPlan.FREE: {
        "properties": 1,  # free users can only list 1 property
        "featured_listings": 0,  # cannot feature properties
    },
    SubscriptionPlan.BASIC: {
        "properties": 5,
        "featured_listings": 1,
    },
    SubscriptionPlan.PREMIUM: {
        "properties": 50,
        "featured_listings": 5,
    },
    SubscriptionPlan.ENTERPRISE: {
        "properties": None,  # unlimited
        "featured_listings": None,  # unlimited
    },
}
