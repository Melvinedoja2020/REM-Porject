from django.conf import settings
from django.templatetags.static import static

FRONTEND_URL = "https://onsite.kleeth.io"


# def _email_frontend_base_url() -> str:
#     """Frontend base URL for email CTA links."""
#     return FRONTEND_URL.rstrip("/")


# def build_project_overview_url(project_id) -> str:
#     """Build frontend URL for project overview tab used by project notifications."""
#     return f"{_email_frontend_base_url()}/project/?id={project_id}&tab=overview"


# def build_project_log_url(project_id, log_id) -> str:
#     """Build frontend URL for logs tab used by log notifications."""
#     return f"{_email_frontend_base_url()}/project/?id={project_id}&tab=logs&logId={log_id}"


def email_base_context() -> dict:
    """Shared email assets and branding"""
    base_url = settings.SITE_URL.rstrip("/")

    return {
        "logo_url": f"{base_url}{static('images/Kleeth.png')}",
        "twitter_icon": f"{base_url}{static('images/twitter.png')}",
        "instagram_icon": f"{base_url}{static('images/IG.png')}",
        "twitter_url": "#",  # can also come from env
        "instagram_url": "#",
        "website": base_url,
    }


def build_email_context(extra: dict | None = None) -> dict:
    """Merge base context with template-specific variables"""
    context = email_base_context()
    if extra:
        context.update(extra)
    return context
