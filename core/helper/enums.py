from django.db.models import TextChoices


class UserRoleChoice(TextChoices):
    CUSTOMER = ("Prospective Buyer/Tenant", "Prospective Buyer/Tenant")
    AGENT = ("Agent", "Agent")
    # REAL_ESTATE_OWNER = ("Real Estate Owner", "Real Estate Owner")


class PROPERTY_TYPES_CHOICES(TextChoices):
    APARTMENT = ("Apartment",    "Apartment")
    HOUSE = ("House", "House")
    STUDIO = ("Studio", "Studio")
    OFFICE = ("Office", "Office")
    EVENT_HALL = ("Event Hall", "Event Hall")


class Lead_Status_Choices(TextChoices):
    NEW = ("New", "New")
    CONTRACTED = ("Contacted", "Contacted")
    SCHEDULED = ("Scheduled", "Scheduled")
    CLOSED = ("Closed", "Closed")


class RentalApplicationChoices(TextChoices):
    PENDING = ("Pending", "Pending")
    APPROVED = ("Approved", "Approved")
    REJECTED = ("Rejected", "Rejected")


class PaymentStatus(TextChoices):
    PENDING = ("Pending", "Pending")
    PAID = ("Paid", "Paid")
    FAILED = ("Failed", "Failed")


class PropertyListingType(TextChoices):
    RENT = ("Rent", "Rent")
    FOR_SALE = ("For Sale", "For Sale")


class AgentTypeChoices(TextChoices):
    REAL_ESTATE_AGENT = ("Real Estate Agent", "Real Estate Agent")
    PROPERTY_MANAGER = ("Property Manager", "Property Manager")


class VerificationStatusChoices(TextChoices):
    PENDING = "pending", "Pending"
    VERIFIED = "verified", "Verified"
    REJECTED = "rejected", "Rejected"
    


