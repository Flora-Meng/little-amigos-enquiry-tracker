import json
from datetime import date
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt

from accounts.authorization import Action, require_permission
from accounts.models import Location, User

from .forms import EnquiryAdminUpdateForm, EnquiryFilterForm, NoteForm, StoreEnquiryForm
from .models import Enquiry, ExtensionToken, Note, ZumoImportDecision
from .routing import normalise_postcode, route_postcode
from .services import apply_status_rules, due_today, find_duplicates, overdue, schedule_next_follow_up


@login_required
def new_store_enquiry(request):
    require_permission(request.user, Action.CREATE_STORE_ENQUIRY)

    if request.method == "POST":
        form = StoreEnquiryForm(request.POST, user=request.user)
        if form.is_valid():
            from accounts.authorization import enquiries_visible_to

            duplicate_matches = find_duplicates(
                enquiries_visible_to(request.user, Enquiry.objects.all()),
                email=form.cleaned_data.get("email", ""),
                phone=form.cleaned_data.get("phone", ""),
            )
            if duplicate_matches.exists() and request.POST.get("confirm_duplicate") != "1":
                return render(
                    request,
                    "enquiries/new_store_enquiry.html",
                    {"form": form, "duplicate_matches": duplicate_matches},
                )
            with transaction.atomic():
                enquiry = form.save(commit=False)
                enquiry.location = (
                    request.user.location
                    if request.user.role == User.Role.STAFF
                    else form.cleaned_data["location"]
                )
                enquiry.source = Enquiry.Source.STORE
                enquiry.status = Enquiry.Status.NEW
                enquiry.submitted_by = request.user
                enquiry.full_clean()
                enquiry.save()

                initial_note = form.cleaned_data["initial_note"].strip()
                if initial_note:
                    Note.objects.create(
                        enquiry=enquiry,
                        body=initial_note,
                        author=request.user,
                        author_display_name=request.user.display_name,
                    )
            messages.success(request, f"Enquiry for {enquiry.name} was created.")
            return redirect("dashboard")
    else:
        form = StoreEnquiryForm(user=request.user)

    return render(request, "enquiries/new_store_enquiry.html", {"form": form})


@login_required
def enquiry_list(request):
    from accounts.authorization import enquiries_visible_to

    queryset = enquiries_visible_to(
        request.user,
        Enquiry.objects.select_related("location", "submitted_by"),
    )
    form = EnquiryFilterForm(request.GET or None, user=request.user)

    if form.is_valid():
        data = form.cleaned_data
        if data.get("archived") == "only":
            queryset = queryset.filter(archived=True)
        elif data.get("archived") != "all":
            queryset = queryset.filter(archived=False)

        search = data.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(phone__icontains=search)
                | Q(email__icontains=search)
            )
        if data.get("location"):
            queryset = queryset.filter(location=data["location"])
        if data.get("source"):
            queryset = queryset.filter(source=data["source"])
        if data.get("status"):
            queryset = queryset.filter(status=data["status"])
        if data.get("party_date"):
            queryset = queryset.filter(party_date=data["party_date"])
        if data.get("created_date"):
            queryset = queryset.filter(created_at__date=data["created_date"])

        if data.get("follow_up") == "due_today":
            queryset = due_today(queryset)
        elif data.get("follow_up") == "overdue":
            queryset = overdue(queryset)

        sort = data.get("sort") or "newest"
    else:
        queryset = queryset.filter(archived=False)
        sort = "newest"

    ordering = {
        "newest": ("-created_at",),
        "updated": ("-updated_at",),
        "party_date": (F("party_date").asc(nulls_last=True), "-created_at"),
    }
    queryset = queryset.order_by(*ordering.get(sort, ordering["newest"]))

    return render(
        request,
        "enquiries/enquiry_list.html",
        {"form": form, "enquiries": queryset, "result_count": queryset.count()},
    )

def _visible_enquiry_or_404(user, enquiry_id):
    from accounts.authorization import enquiries_visible_to

    return get_object_or_404(
        enquiries_visible_to(
            user,
            Enquiry.objects.select_related("location", "submitted_by"),
        ),
        id=enquiry_id,
    )


@login_required
def enquiry_detail(request, enquiry_id):
    enquiry = _visible_enquiry_or_404(request.user, enquiry_id)
    require_permission(request.user, Action.VIEW_ENQUIRY, enquiry=enquiry)
    update_form = EnquiryAdminUpdateForm(instance=enquiry) if request.user.role == User.Role.ADMIN else None
    return render(request, "enquiries/enquiry_detail.html", {
        "enquiry": enquiry,
        "notes": enquiry.notes.select_related("author").all(),
        "note_form": NoteForm(),
        "update_form": update_form,
    })


@login_required
@transaction.atomic
def update_enquiry(request, enquiry_id):
    enquiry = _visible_enquiry_or_404(request.user, enquiry_id)
    require_permission(request.user, Action.EDIT_CUSTOMER, enquiry=enquiry)
    if request.method != "POST":
        return redirect("enquiry_detail", enquiry_id=enquiry.id)

    previous_status = enquiry.status
    form = EnquiryAdminUpdateForm(request.POST, instance=enquiry)
    if form.is_valid():
        updated = form.save(commit=False)
        apply_status_rules(updated, previous_status)
        updated.full_clean()
        updated.save()
        messages.success(request, "Enquiry updated.")
        return redirect("enquiry_detail", enquiry_id=updated.id)

    return render(request, "enquiries/enquiry_detail.html", {
        "enquiry": enquiry,
        "notes": enquiry.notes.select_related("author").all(),
        "note_form": NoteForm(),
        "update_form": form,
    }, status=400)


@login_required
@transaction.atomic
def add_note(request, enquiry_id):
    enquiry = _visible_enquiry_or_404(request.user, enquiry_id)
    require_permission(request.user, Action.ADD_NOTE, enquiry=enquiry)
    if request.method != "POST":
        return redirect("enquiry_detail", enquiry_id=enquiry.id)
    form = NoteForm(request.POST)
    if form.is_valid():
        Note.objects.create(
            enquiry=enquiry,
            body=form.cleaned_data["body"].strip(),
            author=request.user,
            author_display_name=request.user.display_name,
        )
        messages.success(request, "Note added.")
    return redirect("enquiry_detail", enquiry_id=enquiry.id)


@login_required
@transaction.atomic
def archive_enquiry(request, enquiry_id):
    enquiry = _visible_enquiry_or_404(request.user, enquiry_id)
    require_permission(request.user, Action.ARCHIVE_ENQUIRY, enquiry=enquiry)
    if request.method == "POST" and not enquiry.archived:
        enquiry.archived = True
        enquiry.archived_at = timezone.now()
        enquiry.save(update_fields=("archived", "archived_at", "updated_at"))
        messages.success(request, f"{enquiry.name} was archived.")
    return redirect("enquiry_list")


@login_required
@transaction.atomic
def reschedule_follow_up(request, enquiry_id):
    enquiry = _visible_enquiry_or_404(request.user, enquiry_id)
    require_permission(request.user, Action.UPDATE_FOLLOW_UP, enquiry=enquiry)
    if request.method == "POST":
        try:
            schedule_next_follow_up(enquiry)
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            enquiry.save(update_fields=("follow_up_due_date", "updated_at"))
            messages.success(
                request,
                f"Next follow-up scheduled for {enquiry.follow_up_due_date:%-d %B %Y}.",
            )
    return redirect("enquiry_detail", enquiry_id=enquiry.id)


def _zumo_api_admin(*, allow_session=True):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            authorization = request.headers.get("Authorization", "")
            raw_token = authorization[7:].strip() if authorization.startswith("Bearer ") else ""
            extension_token = ExtensionToken.authenticate(raw_token) if raw_token else None
            if extension_token:
                request.user = extension_token.user
                request.extension_token = extension_token
                return view(request, *args, **kwargs)
            if allow_session and request.user.is_authenticated and request.user.is_active:
                if request.user.role == User.Role.ADMIN:
                    return view(request, *args, **kwargs)
                return JsonResponse({"error": "admin_required"}, status=403)
            return JsonResponse({"error": "authentication_required"}, status=401)

        return wrapped

    return decorator


def _json_body(request):
    try:
        return json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


@login_required
def zumo_imports(request):
    require_permission(request.user, Action.ACCESS_ZUMO)
    decisions = ZumoImportDecision.objects.select_related(
        "linked_enquiry", "detected_location", "reviewed_by"
    ).order_by("-reviewed_at")
    return render(
        request,
        "enquiries/zumo_imports.html",
        {
            "decisions": decisions,
            "imported_count": decisions.filter(decision=ZumoImportDecision.Decision.IMPORTED).count(),
            "ignored_count": decisions.filter(decision=ZumoImportDecision.Decision.IGNORED).count(),
            "duplicate_count": decisions.filter(possible_duplicate=True).count(),
            "out_of_area_count": decisions.filter(detected_location__isnull=True).count(),
        },
    )


@require_GET
@_zumo_api_admin()
def zumo_review_status(request, conversation_id):
    decision = ZumoImportDecision.objects.filter(
        zumo_conversation_id=conversation_id
    ).select_related("linked_enquiry").first()
    if decision is None:
        return JsonResponse({"status": "not_reviewed"})
    payload = {
        "status": decision.decision,
        "reviewed_at": decision.reviewed_at.isoformat(),
    }
    if decision.linked_enquiry_id:
        payload["enquiry_id"] = str(decision.linked_enquiry_id)
        payload["enquiry_url"] = request.build_absolute_uri(
            reverse("enquiry_detail", args=(decision.linked_enquiry_id,))
        )
    return JsonResponse(payload)


@csrf_exempt
@require_POST
@_zumo_api_admin(allow_session=False)
@transaction.atomic
def zumo_import(request):
    data = _json_body(request)
    if data is None:
        return JsonResponse({"error": "invalid_json"}, status=400)

    conversation_id = str(data.get("conversation_id", "")).strip()
    conversation_url = str(data.get("conversation_url", "")).strip()
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip()
    phone = str(data.get("phone", "")).strip()
    postcode = normalise_postcode(data.get("postcode", ""))
    if not conversation_id or not conversation_url or not name:
        return JsonResponse(
            {"error": "missing_fields", "fields": ["conversation_id", "conversation_url", "name"]},
            status=422,
        )
    if not email and not phone:
        return JsonResponse({"error": "contact_required"}, status=422)
    if ZumoImportDecision.objects.filter(zumo_conversation_id=conversation_id).exists():
        return JsonResponse({"error": "already_reviewed"}, status=409)

    detected_code = route_postcode(postcode)
    detected_location = Location.objects.filter(code=detected_code).first() if detected_code else None
    override_code = str(data.get("override_location", "")).strip().lower()
    override_location = Location.objects.filter(code=override_code).first() if override_code else None
    if override_code and override_location is None:
        return JsonResponse({"error": "invalid_override_location"}, status=422)
    assigned_location = override_location or detected_location
    if assigned_location is None:
        return JsonResponse(
            {"error": "out_of_area", "detected_postcode": postcode, "can_ignore": True},
            status=422,
        )

    duplicates = find_duplicates(Enquiry.objects.all(), email=email, phone=phone)
    duplicate_payload = [
        {
            "id": str(match.id),
            "name": match.name,
            "location": match.location.code,
            "status": match.status,
            "url": request.build_absolute_uri(reverse("enquiry_detail", args=(match.id,))),
        }
        for match in duplicates.select_related("location")[:10]
    ]
    if duplicate_payload and not data.get("confirm_duplicate"):
        return JsonResponse(
            {"error": "possible_duplicate", "matches": duplicate_payload}, status=409
        )

    party_date = None
    if data.get("party_date"):
        try:
            party_date = date.fromisoformat(str(data["party_date"]))
        except ValueError:
            return JsonResponse({"error": "invalid_party_date"}, status=422)

    enquiry = Enquiry(
        name=name,
        postcode=postcode,
        party_date=party_date,
        party_date_unknown=bool(data.get("party_date_unknown", False)),
        email=email,
        phone=phone,
        location=assigned_location,
        source=Enquiry.Source.ONLINE,
        status=Enquiry.Status.NEW,
        submitted_by=request.user,
        zumo_conversation_id=conversation_id,
        original_zumo_message=str(data.get("original_message", "")),
    )
    try:
        enquiry.full_clean()
    except ValidationError as exc:
        return JsonResponse(
            {"error": "validation_error", "fields": exc.message_dict}, status=422
        )
    enquiry.save()
    ZumoImportDecision.objects.create(
        zumo_conversation_id=conversation_id,
        zumo_conversation_url=conversation_url,
        decision=ZumoImportDecision.Decision.IMPORTED,
        linked_enquiry=enquiry,
        detected_postcode=postcode,
        detected_location=detected_location,
        reviewed_by=request.user,
        original_message_snapshot=str(data.get("original_message", "")),
        possible_duplicate=bool(duplicate_payload),
    )
    return JsonResponse(
        {
            "status": "imported",
            "enquiry_id": str(enquiry.id),
            "enquiry_url": request.build_absolute_uri(reverse("enquiry_detail", args=(enquiry.id,))),
            "assigned_location": assigned_location.code,
        },
        status=201,
    )


@csrf_exempt
@require_POST
@_zumo_api_admin(allow_session=False)
@transaction.atomic
def zumo_ignore(request):
    data = _json_body(request)
    if data is None:
        return JsonResponse({"error": "invalid_json"}, status=400)
    conversation_id = str(data.get("conversation_id", "")).strip()
    conversation_url = str(data.get("conversation_url", "")).strip()
    if not conversation_id or not conversation_url:
        return JsonResponse({"error": "missing_fields"}, status=422)
    if ZumoImportDecision.objects.filter(zumo_conversation_id=conversation_id).exists():
        return JsonResponse({"error": "already_reviewed"}, status=409)
    postcode = normalise_postcode(data.get("postcode", ""))
    detected_code = route_postcode(postcode)
    detected_location = Location.objects.filter(code=detected_code).first() if detected_code else None
    ZumoImportDecision.objects.create(
        zumo_conversation_id=conversation_id,
        zumo_conversation_url=conversation_url,
        decision=ZumoImportDecision.Decision.IGNORED,
        detected_postcode=postcode,
        detected_location=detected_location,
        reviewed_by=request.user,
        original_message_snapshot=str(data.get("original_message", "")),
    )
    return JsonResponse({"status": "ignored"}, status=201)


@require_GET
@_zumo_api_admin()
def zumo_duplicate_check(request):
    matches = find_duplicates(
        Enquiry.objects.all(),
        email=request.GET.get("email", ""),
        phone=request.GET.get("phone", ""),
    ).select_related("location")[:10]
    return JsonResponse(
        {
            "matches": [
                {
                    "id": str(match.id),
                    "name": match.name,
                    "location": match.location.code,
                    "status": match.status,
                    "url": request.build_absolute_uri(
                        reverse("enquiry_detail", args=(match.id,))
                    ),
                }
                for match in matches
            ]
        }
    )


@csrf_exempt
@require_POST
@_zumo_api_admin(allow_session=False)
@transaction.atomic
def zumo_review_again(request, conversation_id):
    decision = ZumoImportDecision.objects.filter(
        zumo_conversation_id=conversation_id,
        decision=ZumoImportDecision.Decision.IGNORED,
    ).first()
    if decision is None:
        return JsonResponse({"error": "ignored_decision_not_found"}, status=404)
    decision.delete()
    return JsonResponse({"status": "not_reviewed"})


@login_required
def extension_token_settings(request):
    require_permission(request.user, Action.ACCESS_ZUMO)
    raw_token = None
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            name = request.POST.get("name", "Flora's Chrome").strip()[:100] or "Chrome extension"
            _, raw_token = ExtensionToken.issue(user=request.user, name=name)
        elif action == "revoke":
            token = get_object_or_404(
                ExtensionToken,
                id=request.POST.get("token_id"),
                user=request.user,
                revoked_at__isnull=True,
            )
            token.revoked_at = timezone.now()
            token.save(update_fields=("revoked_at",))
            messages.success(request, "Extension token revoked.")
            return redirect("extension_token_settings")
    return render(
        request,
        "enquiries/extension_token_settings.html",
        {"tokens": ExtensionToken.objects.filter(user=request.user), "raw_token": raw_token},
    )
