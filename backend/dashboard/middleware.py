from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class LoginRequiredMiddleware:
    """Requires login for every page except an explicit public allowlist."""

    PUBLIC_PATHS = ["/", "/login/", "/signup/", "/logout/"]
    PUBLIC_PREFIXES = ["/static/", "/media/", "/api/", "/admin/"]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        is_public = path in self.PUBLIC_PATHS or any(path.startswith(p) for p in self.PUBLIC_PREFIXES)

        if not is_public and not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={path}")

        return self.get_response(request)


# ---- multi-tenant login enforcement ----
from urllib.parse import quote as _quote
from django.http import JsonResponse as _JsonResponse
from django.shortcuts import redirect as _redirect

_RL_PUBLIC_EXACT = {"/", "/login/", "/logout/", "/favicon.ico"}  # signup closed
_RL_PUBLIC_PREFIX = ("/static/", "/admin/")


class RequireLoginMiddleware:
    """Everything needs a login except the public pages. /api/ is superuser-only."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path == "/signup/":
            return _redirect("/login/")  # signup closed
        if path in _RL_PUBLIC_EXACT or path.startswith(_RL_PUBLIC_PREFIX):
            return self.get_response(request)
        user = request.user
        if not user.is_authenticated:
            if path.startswith("/api/"):
                return _JsonResponse({"detail": "Authentication required."}, status=401)
            return _redirect("/login/?next=" + _quote(request.get_full_path()))
        if path.startswith("/api/") and not user.is_superuser:
            return _JsonResponse({"detail": "Not permitted."}, status=403)
        return self.get_response(request)
