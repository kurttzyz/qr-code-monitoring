"""
URLs for the records app.

Put this file at: records/urls.py
Then include it in your project's root urls.py, e.g.:

    # qr_root/urls.py
    urlpatterns = [
        ...
        path('records/', include('records.urls')),
    ]

That gives you:
    /records/batches/                   -> list (filter ?type=archiving|disposal, ?q=search)
    /records/batches/<pk>/               -> detail
    /records/grds-items/                 -> catalog list
    /records/grds-items/<pk>/            -> catalog detail
    /records/disposal-requests/          -> NAP Form 3 list
    /records/disposal-requests/<pk>/     -> NAP Form 3 detail

QR image + scan-to-redirect for ArchiveBatch are handled by your existing
core app routes (core:qr_image, core:scan) — see scanview_update.py.
"""

from django.urls import path

from records import views

app_name = 'records'

urlpatterns = [
    path('batches/', views.ArchiveBatchListView.as_view(), name='archive_batch_list'),
    path('batches/<int:pk>/', views.ArchiveBatchDetailView.as_view(), name='archive_batch_detail'),

    path('grds-items/', views.GRDSItemListView.as_view(), name='grds_item_list'),
    path('grds-items/<int:pk>/', views.GRDSItemDetailView.as_view(), name='grds_item_detail'),

    path('disposal-requests/', views.DisposalRequestListView.as_view(), name='disposal_request_list'),
    path('disposal-requests/<int:pk>/', views.DisposalRequestDetailView.as_view(), name='disposal_request_detail'),
]