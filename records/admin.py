"""
Admin registration for the records app (NAP-GRDS archiving/disposal tracker).

Put this file at: records/admin.py
Edit the "# >>> EDIT" import below if your app isn't called `records`.
"""

from django.contrib import admin

# >>> EDIT: point this at your real app's models module if different
from records.models import Section, GRDSItem, ArchiveBatch, DisposalRequest  # noqa


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'grds_item_count', 'batch_count')
    search_fields = ('name',)
    ordering = ('name',)

    def grds_item_count(self, obj):
        return obj.grds_items.count()
    grds_item_count.short_description = 'GRDS items'

    def batch_count(self, obj):
        return obj.batches.count()
    batch_count.short_description = 'Batches'


@admin.register(GRDSItem)
class GRDSItemAdmin(admin.ModelAdmin):
    list_display = ('item_no', 'records_series_title', 'retention_period',
                     'default_section', 'is_commonly_used', 'default_scanning_status')
    list_filter = ('is_commonly_used', 'default_scanning_status', 'default_section')
    search_fields = ('item_no', 'records_series_title', 'retention_period')
    ordering = ('item_no',)
    autocomplete_fields = ('default_section',)


class LinkedBatchInline(admin.TabularInline):
    """Shows the other-side batch(es) this one links to/from, read-only."""
    model = ArchiveBatch
    fk_name = 'linked_batch'
    extra = 0
    fields = ('batch_no', 'batch_type', 'batch_date', 'description')
    readonly_fields = fields
    can_delete = False
    verbose_name = "Linked batch (other side)"
    verbose_name_plural = "Linked batches (other side)"

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ArchiveBatch)
class ArchiveBatchAdmin(admin.ModelAdmin):
    list_display = ('batch_no', 'batch_type', 'reference_no', 'box_number', 'batch_date',
                     'grds_item', 'section', 'description', 'disposal_status_value',
                     'is_eligible_for_disposal', 'scanning_status', 'location')
    list_filter = ('batch_type', 'scanning_status', 'section', 'batch_date')
    search_fields = ('batch_no', 'reference_no', 'description', 'grds_item_no_raw', 'location')
    date_hierarchy = 'batch_date'
    ordering = ('-batch_date', 'reference_no')
    autocomplete_fields = ('grds_item', 'section', 'linked_batch')
    inlines = [LinkedBatchInline]

    fieldsets = (
        ('Identification', {
            'fields': ('batch_type', 'reference_no', 'box_number', 'batch_no', 'batch_date')
        }),
        ('Contents', {
            'fields': ('grds_item', 'grds_item_no_raw', 'section', 'description',
                       'period_covered', 'latest_year')
        }),
        ('Retention accounting', {
            'fields': ('years_as_of_count', 'retention_period_years', 'disposal_status_value')
        }),
        ('Status', {
            'fields': ('scanning_status', 'location', 'linked_batch', 'remarks')
        }),
    )

    @admin.display(boolean=True, description='Eligible for disposal')
    def is_eligible_for_disposal(self, obj):
        return obj.is_eligible_for_disposal


@admin.register(DisposalRequest)
class DisposalRequestAdmin(admin.ModelAdmin):
    list_display = ('reference_no', 'status', 'request_date', 'branch_name',
                     'volume_boxes', 'batch_count', 'prepared_by')
    list_filter = ('status', 'request_date')
    search_fields = ('reference_no', 'branch_name', 'location_of_records', 'prepared_by_position')
    date_hierarchy = 'request_date'
    ordering = ('-request_date',)
    autocomplete_fields = ('batches',)
    filter_horizontal = ('batches',)

    fieldsets = (
        ('Request', {
            'fields': ('reference_no', 'status', 'request_date')
        }),
        ('Agency details', {
            'fields': ('agency_name', 'branch_name', 'address', 'telephone_number', 'email_address')
        }),
        ('Records volume', {
            'fields': ('location_of_records', 'volume_boxes', 'volume_cubic_meters')
        }),
        ('Sign-off', {
            'fields': ('prepared_by', 'prepared_by_position', 'noted_by')
        }),
        ('Batches covered', {
            'fields': ('batches',)
        }),
        ('Notes', {
            'fields': ('remarks',)
        }),
    )

    def batch_count(self, obj):
        return obj.batches.count()
    batch_count.short_description = 'Batches'