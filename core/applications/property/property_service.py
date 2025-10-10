

from core.applications.property.models import PropertyType


class PropertyTypeService:
    @staticmethod
    def resolve_property_type(existing_type, new_property_type):
        """
        Return an existing property type or create a new one if provided.
        """
        if new_property_type:
            property_type = PropertyType.objects.filter(
                title__iexact=new_property_type
            ).first()
            if not property_type:
                property_type = PropertyType.objects.create(title=new_property_type)
            return property_type
        return existing_type
