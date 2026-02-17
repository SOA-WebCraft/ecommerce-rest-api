from django.conf import settings
import os
print("cookies.py loaded from:", os.path.abspath(__file__))
print("DEBUG in cookies.py =", settings.DEBUG)

def cookie_kwargs():
    # Force dev-friendly cookies
    if settings.DEBUG:
        return {
            "httponly": True,
            "secure": False,
            "samesite": "Lax",
            "path": "/",
        }

    return {
        "httponly": True,
        "secure": True,
        "samesite": "None",
        "path": "/",
    }

def csrf_cookie_kwargs():
    # CSRF cookie must NOT be HttpOnly
    if settings.DEBUG:
        return {
            "httponly": False,
            "secure": False,
            "samesite": "Lax",
            "path": "/",
        }

    return {
        "httponly": False,
        "secure": True,
        "samesite": "None",
        "path": "/",
    }
