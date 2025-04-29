def favorite_property_ids(request):
    """
    Context processor to get the list of favorite property IDs for the authenticated user.
    This is used to check if a property is favorited by the user.
    """
    if request.user.is_authenticated:
        ids = list(request.user.favorites.values_list("property_id", flat=True))
    else:
        ids = []
    return {"favorite_property_ids": ids}


def favorites_context(request):
    """
    Context processor to check if the user has any favorite properties.
    This is used to display the favorites icon in the navigation bar.
    """
    return {
        'user_has_favorites': request.user.favorites.exists() 
            if request.user.is_authenticated 
            else False
    }
