"""Role-based access helpers used across the project."""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.shortcuts import redirect


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if request.user.role == 'admin' or request.user.role in roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, "You don't have permission to access that page.")
            raise PermissionDenied
        return _wrapped
    return decorator


def not_read_only(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.is_read_only:
            messages.error(request, "Your account has read-only (Auditor) access.")
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return _wrapped


def can_approve_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.can_approve:
            messages.error(request, "Only Managers or Administrators can approve this.")
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return _wrapped
