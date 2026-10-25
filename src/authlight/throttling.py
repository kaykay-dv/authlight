from rest_framework.settings import api_settings
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class _ConfiguredAnonThrottle(AnonRateThrottle):
    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES[self.scope]


class _ConfiguredUserThrottle(UserRateThrottle):
    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES[self.scope]

    def get_cache_key(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return None
        return super().get_cache_key(request, view)


class AnonThrottle(_ConfiguredAnonThrottle):
    scope = "anon"


class UserThrottle(_ConfiguredUserThrottle):
    scope = "user"


class UserCreateAnonThrottle(_ConfiguredAnonThrottle):
    scope = "user_create_anon"


class UserCreateUserThrottle(_ConfiguredUserThrottle):
    scope = "user_create_user"
