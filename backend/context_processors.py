from django.db.models import Q


def notifications_processor(request):
    if not request.user.is_authenticated:
        return {}
    from .models import Notification
    qs = Notification.objects.filter(is_read=False).filter(
        Q(recipient=request.user) | Q(role_target=request.user.role)
    ).order_by('-created_at')[:8]
    return {
        'nav_notifications': qs,
        'nav_notifications_count': qs.count(),
    }
