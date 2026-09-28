from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import connection
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache


def health_check(request):
    """Confirm that the web process and its database connection are healthy."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unhealthy"}, status=503)
    return JsonResponse({"status": "ok"})


@never_cache
def initial_admin_password(request):
    """One-use production bootstrap; remove after the initial password is set."""
    user = get_user_model().objects.get(email="flora@littleamigos.au")
    if user.has_usable_password():
        raise Http404

    errors = []
    if request.method == "POST":
        password = request.POST.get("password", "")
        confirmation = request.POST.get("confirmation", "")
        if password != confirmation:
            errors.append("Passwords do not match.")
        else:
            try:
                validate_password(password, user=user)
            except ValidationError as exc:
                errors.extend(exc.messages)
        if not errors:
            user.set_password(password)
            user.password_reset_required = False
            user.save(update_fields=("password", "password_reset_required", "updated_at"))
            return render(request, "accounts/initial_admin_password.html", {"saved": True})

    return render(request, "accounts/initial_admin_password.html", {"errors": errors})
