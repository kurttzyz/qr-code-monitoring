"""
Views for the records app catalog screens: Archive Batches, GRDS Items,
Disposal Requests.

QR code generation and scan-to-redirect are NOT duplicated here — they're
handled by your existing generic core.QRImageView / core.ScanView, which
now also check ArchiveBatch.qr_token (see scanview_update.py). Templates
should call {% url 'core:qr_image' token=batch.qr_token %} the same way
your Product templates already do.

Put this file at: records/views.py
Edit the "# >>> EDIT" import if your app isn't called `records`.
"""

from django.views.generic import ListView, DetailView

# >>> EDIT: point this at your real app's models module if different
from records.models import ArchiveBatch, GRDSItem, DisposalRequest  # noqa


# records/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages


@login_required
def archive_batch_update_status(request, pk):
    batch = get_object_or_404(ArchiveBatch, pk=pk)
    if request.method == 'POST':
        batch.location = request.POST.get('location', '')
        batch.remarks = request.POST.get('remarks', '')
        batch.save(update_fields=['location', 'remarks', 'updated_at'])
        messages.success(request, 'Batch updated.')
    return redirect('records:archive_batch_detail', pk=batch.pk)


# ----------------------------------------------------------------------
# Archive Batches (the main "Products"-equivalent screen)
# ----------------------------------------------------------------------

class ArchiveBatchListView(ListView):
    model = ArchiveBatch
    template_name = 'records/archive_batch_list.html'
    context_object_name = 'batches'
    paginate_by = 25

    def get_queryset(self):
        qs = ArchiveBatch.objects.select_related('grds_item', 'section', 'linked_batch')
        batch_type = self.request.GET.get('type')
        q = self.request.GET.get('q')
        if batch_type in ('archiving', 'disposal'):
            qs = qs.filter(batch_type=batch_type)
        if q:
            qs = qs.filter(batch_no__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_type'] = self.request.GET.get('type', '')
        ctx['query'] = self.request.GET.get('q', '')
        return ctx


class ArchiveBatchDetailView(DetailView):
    model = ArchiveBatch
    template_name = 'records/archive_batch_detail.html'
    context_object_name = 'batch'

    def get_queryset(self):
        return ArchiveBatch.objects.select_related('grds_item', 'section', 'linked_batch')


# ----------------------------------------------------------------------
# GRDS Items (the retention-schedule catalog)
# ----------------------------------------------------------------------

class GRDSItemListView(ListView):
    model = GRDSItem
    template_name = 'records/grds_item_list.html'
    context_object_name = 'items'
    paginate_by = 25

    def get_queryset(self):
        qs = GRDSItem.objects.select_related('default_section')
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(records_series_title__icontains=q)
        return qs


class GRDSItemDetailView(DetailView):
    model = GRDSItem
    template_name = 'records/grds_item_detail.html'
    context_object_name = 'item'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['batches'] = self.object.batches.select_related('section')[:50]
        return ctx


# ----------------------------------------------------------------------
# Disposal Requests (NAP Form 3)
# ----------------------------------------------------------------------

class DisposalRequestListView(ListView):
    model = DisposalRequest
    template_name = 'records/disposal_request_list.html'
    context_object_name = 'requests'
    paginate_by = 25

    def get_queryset(self):
        return DisposalRequest.objects.order_by('-request_date')


class DisposalRequestDetailView(DetailView):
    model = DisposalRequest
    template_name = 'records/disposal_request_detail.html'
    context_object_name = 'disposal_request'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['batches'] = self.object.batches.select_related('grds_item', 'section')
        return ctx