from django.http import HttpResponse
from django.shortcuts import redirect
from .models import User


def _redirect_to_login(request):
    """
    Build the correct 'not authenticated' response.

    Plain requests get a normal 302 redirect.
    HTMX requests get an HX-Redirect header instead — this tells HTMX to do
    a full browser navigation (window.location) rather than swapping the
    login page's HTML into whatever partial target (#drop-area, #saved,
    etc.) triggered the request.
    """
    login_url = f"/login/?next={request.path}"

    if request.headers.get("HX-Request") == "true":
        response = HttpResponse(status=200)
        response["HX-Redirect"] = login_url
        return response

    return redirect(login_url)


def login_require(view_func):
    def wrapper(request, *args, **kwargs):
        auth_token = request.COOKIES.get("auth_token")
        if not auth_token:
            return _redirect_to_login(request)

        try:
            # Unsigned later in verify_token
            parts = auth_token.split(":")
            user_id = parts[0]  # Works now since token = "1234:uuid:signature"
        except:
            return _redirect_to_login(request)

        try:
            user = User.objects.get(id=user_id)
            if user.verify_token(auth_token):
                request.user = user
                return view_func(request, *args, **kwargs)
        except User.DoesNotExist:
            return _redirect_to_login(request)

        return _redirect_to_login(request)
    return wrapper
