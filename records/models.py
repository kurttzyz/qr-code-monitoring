"""
Models for the ILIGAN NAP-GRDS Monitoring, Batching & Labeling System.

This is a *separate* Django app from the supplies-inventory models — it
tracks physical records boxes through their lifecycle (archived -> eligible
for disposal -> disposed), per the National Archives of the Philippines'
General Records Disposition Schedule (GRDS).

Suggested placement: create a new app, e.g.

    python manage.py startapp records

...and put this file at records/models.py. It reuses TimeStampedModel from
your existing core app for consistency — edit the import below if your app
is named differently.

SHEET -> MODEL MAPPING
-----------------------
- REFERENCE, BRANCH COMMONLY USED ITEMS  -> Section, GRDSItem   (the catalog)
- DATA ENTRY FOR DISPOSAL                -> ArchiveBatch (batch_type=DISPOSAL)
- DATA ENTRY ARCHIVING                   -> ArchiveBatch (batch_type=ARCHIVING)
- NAP Form 3 ADMIN USE ONLY (B1..B4)     -> DisposalRequest
- LABEL FORM - FOR DISPOSAL              -> NOT a model; generate this label
- LABEL FORM - FOR ARCHIVING             -> NOT a model; generate this label
                                             on the fly from ArchiveBatch /
                                             DisposalRequest data when printing.
- Sheet1 (bare list of batch numbers)    -> NOT a model; this is just an ad hoc
                                             "flagged for disposal" scratch list —
                                             represented properly by the M2M on
                                             DisposalRequest.batches instead.
"""

from django.conf import settings
from django.db import models
from django.urls import reverse
import uuid

# >>> EDIT: reuse your existing abstract base if you have one
from backend.models import TimeStampedModel  # noqa


# =====================================================================
# CATALOG (REFERENCE sheet + BRANCH COMMONLY USED ITEMS sheet)
# =====================================================================

class Section(TimeStampedModel):
    """A branch section/department that owns records, e.g. 'TELLERING
    SECTION', 'MEMBER SERVICES SECTION'. Also doubles as the SO/branch list
    that appears in the REFERENCE sheet's second block (e.g. 'MARAWI SO')."""
    name = models.CharField(max_length=150, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class GRDSItem(TimeStampedModel):
    """The official GRDS catalog: one row per records series and its
    government-mandated retention period. Sourced from REFERENCE and
    cross-checked against BRANCH COMMONLY USED ITEMS."""

    class ScanningStatus(models.TextChoices):
        SCANNED = 'scanned', 'Scanned'
        UNSCANNED = 'unscanned', 'Unscanned'
        NOT_APPLICABLE = 'not_applicable', 'Not Applicable'

    item_no = models.CharField(
        max_length=30, unique=True,
        help_text="GRDS Item No. as printed in the schedule, e.g. 'SSSRDS 9', '74', '26'.")
    records_series_title = models.CharField(max_length=255)
    retention_period = models.CharField(
        max_length=150,
        help_text="Free text as GRDS defines it, e.g. '1 YEAR', "
                  "'10 YEARS POST-AUDITED, FINALLY SETTLED...', or "
                  "'TO BE FILED WITH APPROPRIATE RECORDS SERIES'.")
    default_section = models.ForeignKey(
        Section, on_delete=models.SET_NULL, null=True, blank=True, related_name='grds_items')
    is_commonly_used = models.BooleanField(
        default=False, help_text="Appears on the branch's BRANCH COMMONLY USED ITEMS shortlist.")
    default_scanning_status = models.CharField(
        max_length=20, choices=ScanningStatus.choices, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['item_no']

    def __str__(self):
        return f"{self.item_no} - {self.records_series_title}"

    def get_absolute_url(self):
        return reverse('records:grdsitem_detail', args=[self.pk])


# =====================================================================
# BOXES / BATCHES (DATA ENTRY FOR DISPOSAL + DATA ENTRY ARCHIVING)
# =====================================================================

class ArchiveBatch(TimeStampedModel):
    """One physical box/folder of records, at either the 'still archived'
    or 'flagged/processed for disposal' stage of its lifecycle. Both source
    sheets share almost identical columns, so a single model with a
    `batch_type` flag replaces both, and `linked_batch` connects a disposal
    row back to the archiving row it graduated from ('BATCH NO FROM
    ARCHIVES' / 'STATUS BATCH NO DISPOSAL' in the two sheets)."""

    class BatchType(models.TextChoices):
        ARCHIVING = 'archiving', 'Archiving'
        DISPOSAL = 'disposal', 'Disposal'

    class ScanningStatus(models.TextChoices):
        SCANNED = 'scanned', 'Scanned'
        UNSCANNED = 'unscanned', 'Unscanned'
        NOT_APPLICABLE = 'not_applicable', 'Not Applicable'

    class LocationChoices(models.TextChoices):
        RIMS_CDO = 'rims_cdo', 'RIMS CDO'
        ARCHIVE_ROOM = 'archive_room', 'Archive Room'
        BRANCH_STOCKROOM = 'branch_stockroom', 'Branch Stockroom'
        OFFSITE_STORAGE = 'offsite_storage', 'Offsite Storage'
        DISPOSED_THRU_NAP = 'disposed_thru_nap', 'Disposed thru NAP'

    batch_type = models.CharField(max_length=10, choices=BatchType.choices)
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # Identifiers straight off the sheet
    reference_no = models.CharField(
        max_length=50, db_index=True,
        help_text="Grouping reference for the whole box batch, e.g. 'H02-23-001' or 'ARCH-24-001'.")
    box_number = models.CharField(
        max_length=20, help_text="'BOX #' — kept as text since the sheet has values like '45-1'.")
    batch_no = models.CharField(
        max_length=50, unique=True,
        help_text="Unique per-item batch code, e.g. 'H02-23-0011' (REFERENCE NO + BOX #).")
    batch_date = models.DateField()

    # What's inside
    grds_item = models.ForeignKey(
        GRDSItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='batches')
    grds_item_no_raw = models.CharField(
        max_length=30, blank=True,
        help_text="Fallback copy of the sheet's GRDS ITEM NO text when it didn't match the catalog.")
    section = models.ForeignKey(
        Section, on_delete=models.SET_NULL, null=True, blank=True, related_name='batches')
    description = models.CharField(max_length=255)
    period_covered = models.CharField(
        max_length=255, blank=True,
        help_text="Free text as written on the sheet, e.g. '2015-2018' or 'JAN-DEC 2016'.")
    latest_year = models.PositiveIntegerField(null=True, blank=True)

    # Retention accounting
    years_as_of_count = models.IntegerField(
        null=True, blank=True, help_text="'NO. YEARS AS OF <year>' column.")
    retention_period_years = models.PositiveIntegerField(
        null=True, blank=True, help_text="Numeric retention period used for the batch's own math.")
    disposal_status_value = models.IntegerField(
        null=True, blank=True,
        help_text="The sheet's 'STATUS (GREEN: for DISPOSAL)' value: years_as_of_count minus "
                  "retention_period_years. Zero or positive generally means it's eligible.")

    scanning_status = models.CharField(max_length=20, choices=ScanningStatus.choices, blank=True)
    
    location = models.CharField(
        max_length=150, blank=True, choices=LocationChoices.choices,
        help_text="Current whereabouts/disposition.")

    linked_batch = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='linked_batches',
        help_text="Cross-reference to the corresponding row in the other sheet: "
                  "on a DISPOSAL batch, points at the ARCHIVING batch it came from "
                  "('BATCH NO FROM ARCHIVES'); on an ARCHIVING batch, points at the "
                  "DISPOSAL batch it graduated to once processed.")

    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ['-batch_date', 'reference_no']
        verbose_name_plural = 'Archive batches'

    def __str__(self):
        return f"{self.batch_no} ({self.get_batch_type_display()})"

    def get_absolute_url(self):
        return reverse('records:archivebatch_detail', args=[self.pk])

    @property
    def is_eligible_for_disposal(self):
        if self.disposal_status_value is None:
            return False
        return self.disposal_status_value >= 0


# =====================================================================
# NAP FORM 3 - Request for Authority to Dispose of Records
# =====================================================================

class DisposalRequest(TimeStampedModel):
    """The official government submission (NAP Form No. 3) requesting
    authority to dispose of a set of ArchiveBatch boxes. One request
    typically bundles many batches sharing a disposal run."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SUBMITTED = 'submitted', 'Submitted to NAP'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    reference_no = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT)
    request_date = models.DateField()

    agency_name = models.CharField(max_length=200, default='SOCIAL SECURITY SYSTEM')
    branch_name = models.CharField(max_length=150, blank=True)
    address = models.TextField(blank=True)
    telephone_number = models.CharField(max_length=30, blank=True)
    email_address = models.EmailField(blank=True)

    location_of_records = models.CharField(max_length=200, blank=True)
    volume_boxes = models.PositiveIntegerField(null=True, blank=True)
    volume_cubic_meters = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='disposal_requests_prepared')
    prepared_by_position = models.CharField(max_length=150, blank=True)
    noted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='disposal_requests_noted')

    batches = models.ManyToManyField(
        ArchiveBatch, related_name='disposal_requests', blank=True,
        limit_choices_to={'batch_type': ArchiveBatch.BatchType.DISPOSAL})

    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ['-request_date']

    def __str__(self):
        return f"{self.reference_no} - {self.get_status_display()}"

    def get_absolute_url(self):
        return reverse('records:disposalrequest_detail', args=[self.pk])