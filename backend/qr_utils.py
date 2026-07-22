import io
import qrcode
from django.http import HttpResponse
from django.urls import reverse


def build_scan_url(request, token):
    path = reverse('core:scan', args=[token])
    return request.build_absolute_uri(path)


def qr_png_response(data, box_size=8, border=2):
    img = qrcode.make(data, box_size=box_size, border=border)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return HttpResponse(buf.getvalue(), content_type='image/png')
