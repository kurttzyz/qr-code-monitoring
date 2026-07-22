"""
All URL patterns for the single 'backend' app, grouped into four logical
sections. qr_root/urls.py includes each list under its own namespace, so
templates keep using names like {% url 'core:product_list' %},
{% url 'operations:receiving_list' %}, {% url 'accounts:login' %}, and
{% url 'dashboard:home' %} even though everything lives in one app.
"""
from django.urls import path
from . import views

# ---------------- accounts ----------------
accounts_patterns = [
    path('login/', views.WarehouseLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
]

# ---------------- core (catalog, locations, QR) ----------------
core_patterns = [
    path('warehouses/', views.WarehouseListView.as_view(), name='warehouse_list'),
    path('warehouses/add/', views.WarehouseCreateView.as_view(), name='warehouse_add'),
    path('warehouses/<int:pk>/edit/', views.WarehouseUpdateView.as_view(), name='warehouse_edit'),
    path('warehouses/<int:pk>/delete/', views.WarehouseDeleteView.as_view(), name='warehouse_delete'),

    path('locations/', views.LocationListView.as_view(), name='location_list'),
    path('locations/add/', views.LocationCreateView.as_view(), name='location_add'),
    path('locations/<int:pk>/', views.LocationDetailView.as_view(), name='location_detail'),
    path('locations/<int:pk>/edit/', views.LocationUpdateView.as_view(), name='location_edit'),
    path('locations/<int:pk>/delete/', views.LocationDeleteView.as_view(), name='location_delete'),

    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/add/', views.CategoryCreateView.as_view(), name='category_add'),
    path('categories/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_edit'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),

    path('units/', views.UnitListView.as_view(), name='unit_list'),
    path('units/add/', views.UnitCreateView.as_view(), name='unit_add'),
    path('units/<int:pk>/edit/', views.UnitUpdateView.as_view(), name='unit_edit'),
    path('units/<int:pk>/delete/', views.UnitDeleteView.as_view(), name='unit_delete'),

    path('suppliers/', views.SupplierListView.as_view(), name='supplier_list'),
    path('suppliers/add/', views.SupplierCreateView.as_view(), name='supplier_add'),
    path('suppliers/<int:pk>/edit/', views.SupplierUpdateView.as_view(), name='supplier_edit'),
    path('suppliers/<int:pk>/delete/', views.SupplierDeleteView.as_view(), name='supplier_delete'),

    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/add/', views.ProductCreateView.as_view(), name='product_add'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('products/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product_edit'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),

    path('batches/', views.ProductBatchListView.as_view(), name='batch_list'),
    path('batches/add/', views.ProductBatchCreateView.as_view(), name='batch_add'),
    path('batches/<int:pk>/edit/', views.ProductBatchUpdateView.as_view(), name='batch_edit'),

    path('assets/', views.AssetListView.as_view(), name='asset_list'),
    path('assets/add/', views.AssetCreateView.as_view(), name='asset_add'),
    path('assets/<int:pk>/', views.AssetDetailView.as_view(), name='asset_detail'),
    path('assets/<int:pk>/edit/', views.AssetUpdateView.as_view(), name='asset_edit'),

    path('qr/<uuid:token>.png', views.QRImageView.as_view(), name='qr_image'),
    path('scan/<uuid:token>/', views.ScanView.as_view(), name='scan'),
    path('scanner/', views.ScannerPageView.as_view(), name='scanner'),
]

# ---------------- operations (workflows) ----------------
operations_patterns = [
    path('receiving/', views.ReceivingListView.as_view(), name='receiving_list'),
    path('receiving/add/', views.receiving_create, name='receiving_add'),
    path('receiving/<int:pk>/', views.receiving_detail, name='receiving_detail'),
    path('receiving/<int:pk>/store/', views.receiving_store, name='receiving_store'),

    path('transfers/', views.TransferListView.as_view(), name='transfer_list'),
    path('transfers/add/', views.transfer_create, name='transfer_add'),
    path('transfers/<int:pk>/', views.transfer_detail, name='transfer_detail'),
    path('transfers/<int:pk>/approve/', views.transfer_approve, name='transfer_approve'),
    path('transfers/<int:pk>/process/', views.transfer_process, name='transfer_process'),

    path('requests/', views.RequestListView.as_view(), name='request_list'),
    path('requests/add/', views.request_create, name='request_add'),
    path('requests/<int:pk>/', views.request_detail, name='request_detail'),
    path('requests/<int:pk>/<str:decision>/', views.request_review, name='request_review'),

    path('releases/', views.ReleaseListView.as_view(), name='release_list'),
    path('releases/add/', views.release_create, name='release_add'),
    path('releases/from-request/<int:request_pk>/', views.release_create, name='release_from_request'),
    path('releases/<int:pk>/', views.release_detail, name='release_detail'),

    path('returns/', views.ReturnListView.as_view(), name='return_list'),
    path('returns/add/', views.return_create, name='return_add'),
    path('returns/<int:pk>/', views.return_detail, name='return_detail'),

    path('counts/', views.CountListView.as_view(), name='count_list'),
    path('counts/add/', views.count_create, name='count_add'),
    path('counts/<int:pk>/', views.count_detail, name='count_detail'),
    path('counts/<int:pk>/items/<int:item_pk>/enter/', views.count_entry, name='count_entry'),
    path('counts/<int:pk>/approve/', views.count_approve, name='count_approve'),

    path('damage/', views.DamageListView.as_view(), name='damage_list'),
    path('damage/add/', views.damage_create, name='damage_add'),
    path('damage/<int:pk>/', views.damage_detail, name='damage_detail'),
    path('damage/<int:pk>/approve/', views.damage_approve, name='damage_approve'),
    path('disposals/', views.DisposalListView.as_view(), name='disposal_list'),
    path('disposals/add/', views.disposal_create, name='disposal_add'),
]

# ---------------- dashboard (home, notifications, reports) ----------------
dashboard_patterns = [
    path('', views.home, name='home'),
    path('notifications/', views.notifications_all, name='notifications'),
    path('notifications/<int:pk>/read/', views.notification_mark_read, name='notification_read'),
    path('audit-log/', views.audit_log, name='audit_log'),

    path('reports/', views.reports_home, name='reports_home'),
    path('reports/stock/', views.report_stock, name='report_stock'),
    path('reports/movement/', views.report_movement, name='report_movement'),
    path('reports/low-stock/', views.report_low_stock, name='report_low_stock'),
    path('reports/expiration/', views.report_expiration, name='report_expiration'),
]
