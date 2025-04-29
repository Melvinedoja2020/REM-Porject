from django.db.models import TextChoices


class UserRoleChoice(TextChoices):
    CUSTOMER = ("Prospective Buyer/Tenant", "Prospective Buyer/Tenant")
    AGENT = ("Agent", "Agent")
    # REAL_ESTATE_OWNER = ("Real Estate Owner", "Real Estate Owner")


class PropertyTypeChoices(TextChoices):
    APARTMENT = ("apartment", "Apartment")
    HOUSE = ("house", "House")
    STUDIO = ("studio", "Studio")
    VILLA = ("villa", "Villa")
    DUPLEX = ("duplex", "Duplex")
    BUNGALOW = ("bungalow", "Bungalow")
    PENTHOUSE = ("penthouse", "Penthouse")
    TOWNHOUSE = ("townhouse", "Townhouse")
    CONDO = ("condo", "Condominium")
    LAND = ("land", "Land")
    OFFICE = ("office", "Office Space")
    SHOP = ("shop", "Shop")
    WAREHOUSE = ("warehouse", "Warehouse")
    FARM = ("farm", "Farm / Agricultural")
    OTHER = ("other", "Other")



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
    


class NotificationType(TextChoices):
    NEW_LISTING = ("New Listing", "New Listing")
    PRICE_CHANGING = ("Price changing", "Price changing")
    MESSAGE = ("Message", "Message")
    VIEWING = ("Viewing", "Viewing")
    FAVORITE = ("Favorite", "Favorite")