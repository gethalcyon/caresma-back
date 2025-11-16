from app.core.users import current_active_user, current_superuser
from app.models.user import User

# Export dependencies for use in routes
get_current_user = current_active_user
get_current_active_superuser = current_superuser

__all__ = ["get_current_user", "get_current_active_superuser", "User"]
