from django.http import HttpResponse
from django.shortcuts import redirect
from .models import User
def login_require(view_func):
    def wrapper(request, *args, **kwargs):
        auth_token = request.COOKIES.get("auth_token")
        if not auth_token:
            return redirect("signup")

        try:
            # Unsigned later in verify_token
            parts = auth_token.split(":")
            user_id = parts[0]  # Works now since token = "1234:uuid:signature"
        except:
            return HttpResponse("Invalid token format", status=401)

        try:
            user = User.objects.get(id=user_id)
            if user.verify_token(auth_token):
                request.user = user
                return view_func(request, *args, **kwargs)
        except User.DoesNotExist:
            return HttpResponse("Invalid user", status=401)

        return HttpResponse("Invalid token", status=401)
    return wrapper
