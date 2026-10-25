from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render

LOCKOUT_DETAIL = "Too many failed login attempts."


def lockout_response(request, original_response=None, credentials=None):
    """JSON 403 for API clients. Admin keeps Axes' default lockout response."""
    path = getattr(request, "path", "") or ""
    if path.startswith("/api/"):
        return JsonResponse({"detail": LOCKOUT_DETAIL}, status=403)

    from axes.helpers import (
        get_client_username,
        get_cool_off,
        get_cool_off_iso8601,
        get_failure_limit,
        get_lockout_message,
    )

    status = settings.AXES_HTTP_RESPONSE_CODE
    context = {
        "failure_limit": get_failure_limit(request, credentials),
        "username": get_client_username(request, credentials) or "",
    }
    cool_off = get_cool_off(request)
    if cool_off:
        context.update(
            {
                "cooloff_time": get_cool_off_iso8601(cool_off),
                "cooloff_timedelta": cool_off,
            }
        )

    if settings.AXES_LOCKOUT_TEMPLATE:
        return render(
            request,
            settings.AXES_LOCKOUT_TEMPLATE,
            context,
            status=status,
        )
    if settings.AXES_LOCKOUT_URL:
        query_string = urlencode({"username": context["username"]})
        return redirect(f"{settings.AXES_LOCKOUT_URL}?{query_string}")
    return HttpResponse(get_lockout_message(), status=status)
