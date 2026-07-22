from django import template

register = template.Library()


@register.filter
def get_attr(obj, field_name):
    if obj is None:
        return ''
    value = obj
    for part in str(field_name).split('.'):
        try:
            value = getattr(value, part)
        except AttributeError:
            try:
                value = value[part]
            except (TypeError, KeyError):
                return ''
    if callable(value):
        value = value()
    return value


@register.filter
def status_badge(value):
    mapping = {
        'draft': 'secondary', 'pending': 'warning', 'for_inspection': 'warning',
        'approved': 'success', 'accepted': 'success', 'stored': 'success', 'released': 'success',
        'received': 'success', 'confirmed': 'success', 'matched': 'success', 'adjusted': 'success',
        'closed': 'success', 'complete': 'success',
        'rejected': 'danger', 'cancelled': 'danger', 'for_investigation': 'danger', 'missing': 'danger',
        'partially_accepted': 'info', 'partially_released': 'info', 'in_transit': 'info', 'counting': 'info',
        'for_review': 'info', 'processed': 'success', 'reported': 'warning', 'disposed': 'secondary',
        'available': 'success', 'assigned': 'info', 'in_repair': 'warning', 'condemned': 'danger',
        'good': 'success', 'used': 'secondary', 'damaged': 'danger', 'for_repair': 'warning',
        'missing_parts': 'danger', True: 'success', False: 'secondary',
    }
    return mapping.get(value, 'secondary')
