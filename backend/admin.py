from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (User, Warehouse, WarehouseLocation, Category, Unit, Supplier, Product,
                      ProductBatch, Asset, StockBalance, StockTransaction, AuditLog, Notification,
                      Receiving, ReceivingItem, StockTransfer, StockTransferItem,
                      ItemRequest, ItemRequestItem, StockRelease, StockReleaseItem,
                      Return, ReturnItem, InventoryCount, InventoryCountItem,
                      DamageReport, Disposal)


# ---------------- Accounts ----------------

@admin.register(User)
class WarehouseUserAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'role', 'department', 'is_active_employee', 'is_staff')
    list_filter = ('role', 'department', 'is_active_employee')
    fieldsets = UserAdmin.fieldsets + (
        ('Warehouse Info', {'fields': ('role', 'employee_id', 'department', 'phone', 'is_active_employee')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Warehouse Info', {'fields': ('role', 'employee_id', 'department', 'phone', 'email')}),
    )


# ---------------- Catalog ----------------

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active')
    search_fields = ('code', 'name')
    list_filter = ('is_active',)


@admin.register(WarehouseLocation)
class WarehouseLocationAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'warehouse', 'location_type', 'parent', 'is_active', 'qr_token')
    list_filter = ('warehouse', 'location_type', 'is_active')
    search_fields = ('code', 'name')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbreviation')


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('code', 'company_name', 'contact_person', 'email', 'phone', 'is_active')
    search_fields = ('code', 'company_name')
    list_filter = ('is_active',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'category', 'unit', 'tracking_type', 'total_stock', 'reorder_level', 'is_active')
    search_fields = ('sku', 'name', 'barcode')
    list_filter = ('category', 'tracking_type', 'is_active')


@admin.register(ProductBatch)
class ProductBatchAdmin(admin.ModelAdmin):
    list_display = ('product', 'batch_number', 'expiration_date', 'supplier')
    search_fields = ('batch_number', 'product__name', 'product__sku')
    list_filter = ('supplier',)


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('asset_code', 'product', 'serial_number', 'location', 'condition', 'status', 'assigned_to')
    search_fields = ('asset_code', 'serial_number')
    list_filter = ('condition', 'status', 'location__warehouse')


# ---------------- Stock ledger ----------------

@admin.register(StockBalance)
class StockBalanceAdmin(admin.ModelAdmin):
    list_display = ('product', 'batch', 'location', 'quantity')
    search_fields = ('product__sku', 'product__name')
    list_filter = ('location__warehouse',)


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'transaction_type', 'product', 'location', 'quantity', 'balance_after', 'performed_by', 'created_at')
    list_filter = ('transaction_type', 'location__warehouse', 'created_at')
    search_fields = ('reference_number', 'product__sku', 'product__name')
    date_hierarchy = 'created_at'

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'model_name', 'object_id')
    list_filter = ('action', 'model_name')
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('message', 'level', 'recipient', 'role_target', 'is_read', 'created_at')
    list_filter = ('level', 'is_read', 'role_target')


# ---------------- Operations ----------------

class ReceivingItemInline(admin.TabularInline):
    model = ReceivingItem
    extra = 0


@admin.register(Receiving)
class ReceivingAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'supplier', 'warehouse', 'status', 'received_by', 'created_at')
    list_filter = ('status', 'warehouse')
    search_fields = ('reference_number',)
    inlines = [ReceivingItemInline]


class StockTransferItemInline(admin.TabularInline):
    model = StockTransferItem
    extra = 0


@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'source_location', 'destination_location', 'status', 'requested_by', 'created_at')
    list_filter = ('status',)
    inlines = [StockTransferItemInline]


class ItemRequestItemInline(admin.TabularInline):
    model = ItemRequestItem
    extra = 0


@admin.register(ItemRequest)
class ItemRequestAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'department', 'requested_by', 'status', 'created_at')
    list_filter = ('status', 'department')
    inlines = [ItemRequestItemInline]


class StockReleaseItemInline(admin.TabularInline):
    model = StockReleaseItem
    extra = 0


@admin.register(StockRelease)
class StockReleaseAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'released_to_department', 'recipient_name', 'status', 'created_at')
    inlines = [StockReleaseItemInline]


class ReturnItemInline(admin.TabularInline):
    model = ReturnItem
    extra = 0


@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'returned_by', 'department', 'status', 'created_at')
    inlines = [ReturnItemInline]


class InventoryCountItemInline(admin.TabularInline):
    model = InventoryCountItem
    extra = 0


@admin.register(InventoryCount)
class InventoryCountAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'warehouse', 'location', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'warehouse')
    inlines = [InventoryCountItemInline]


@admin.register(DamageReport)
class DamageReportAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'product', 'quantity', 'status', 'reported_by', 'created_at')
    list_filter = ('status',)


@admin.register(Disposal)
class DisposalAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'product', 'quantity', 'method', 'approved_by', 'created_at')


# Customize Django Admin
admin.site.site_header = "Administration"
admin.site.site_title = "Administration"
admin.site.index_title = "Administration"