import uuid
import datetime
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


# =====================================================================
# ACCOUNTS / USERS
# =====================================================================

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrator'
        MANAGER = 'manager', 'Warehouse Manager'
        STAFF = 'staff', 'Warehouse Staff'
        REQUESTER = 'requester', 'Requesting Department'
        AUDITOR = 'auditor', 'Auditor / Viewer'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STAFF)
    employee_id = models.CharField(max_length=30, blank=True)
    department = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_active_employee = models.BooleanField(default=True)

    def has_role(self, *roles):
        return self.role in roles

    @property
    def can_approve(self):
        return self.role in (self.Role.ADMIN, self.Role.MANAGER)

    @property
    def is_read_only(self):
        return self.role == self.Role.AUDITOR

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# =====================================================================
# CATALOG / MASTER DATA
# =====================================================================

class Warehouse(TimeStampedModel):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=150)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"


class WarehouseLocation(TimeStampedModel):
    class LocationType(models.TextChoices):
        ZONE = 'zone', 'Zone'
        RACK = 'rack', 'Rack'
        SHELF = 'shelf', 'Shelf'
        BIN = 'bin', 'Bin'

    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='locations')
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=150)
    location_type = models.CharField(max_length=10, choices=LocationType.choices, default=LocationType.BIN)
    parent = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='children')
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['warehouse', 'code']
        constraints = [
            models.UniqueConstraint(fields=['warehouse', 'code'], name='unique_location_code_per_warehouse')
        ]

    def __str__(self):
        return f"{self.warehouse.code} / {self.code} - {self.name}"

    def full_path(self):
        parts, node = [self.name], self.parent
        while node:
            parts.insert(0, node.name)
            node = node.parent
        return " / ".join(parts)

    def get_absolute_url(self):
        return reverse('core:location_detail', args=[self.pk])


class Category(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Unit(TimeStampedModel):
    name = models.CharField(max_length=60, unique=True)
    abbreviation = models.CharField(max_length=10)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.abbreviation})"


class Supplier(TimeStampedModel):
    code = models.CharField(max_length=30, unique=True)
    company_name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    tax_id = models.CharField(max_length=60, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['company_name']

    def __str__(self):
        return self.company_name


class Product(TimeStampedModel):
    class TrackingType(models.TextChoices):
        QUANTITY = 'quantity', 'Quantity-Based'
        INDIVIDUAL = 'individual', 'Individual Asset'

    sku = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='products')
    tracking_type = models.CharField(max_length=20, choices=TrackingType.choices, default=TrackingType.QUANTITY)
    brand = models.CharField(max_length=120, blank=True)
    barcode = models.CharField(max_length=100, blank=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    minimum_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    maximum_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    reorder_level = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.sku} - {self.name}"

    def get_absolute_url(self):
        return reverse('core:product_detail', args=[self.pk])

    @property
    def total_stock(self):
        return self.stock_balances.aggregate(total=models.Sum('quantity'))['total'] or 0

    @property
    def is_low_stock(self):
        return self.total_stock <= self.reorder_level

    @property
    def is_out_of_stock(self):
        return self.total_stock <= 0


class ProductBatch(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='batches')
    batch_number = models.CharField(max_length=100)
    manufacturing_date = models.DateField(null=True, blank=True)
    expiration_date = models.DateField(null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['product', 'batch_number'], name='unique_batch_per_product')
        ]

    def __str__(self):
        return f"{self.product.sku} / {self.batch_number}"

    @property
    def is_expired(self):
        from django.utils import timezone
        return bool(self.expiration_date and self.expiration_date < timezone.localdate())

    @property
    def is_expiring_soon(self):
        from django.utils import timezone
        if not self.expiration_date:
            return False
        return self.expiration_date <= timezone.localdate() + datetime.timedelta(days=30)


class Asset(TimeStampedModel):
    class Condition(models.TextChoices):
        GOOD = 'good', 'Good'
        FAIR = 'fair', 'Fair'
        FOR_REPAIR = 'for_repair', 'For Repair'
        DAMAGED = 'damaged', 'Damaged'
        CONDEMNED = 'condemned', 'Condemned'

    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        ASSIGNED = 'assigned', 'Assigned'
        IN_REPAIR = 'in_repair', 'In Repair'
        DISPOSED = 'disposed', 'Disposed'
        MISSING = 'missing', 'Missing'

    asset_code = models.CharField(max_length=30, unique=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='assets')
    serial_number = models.CharField(max_length=150, blank=True)
    location = models.ForeignKey(WarehouseLocation, on_delete=models.PROTECT, related_name='assets')
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.GOOD)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_assets')
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['asset_code']

    def __str__(self):
        return f"{self.asset_code} - {self.product.name}"


# =====================================================================
# STOCK BALANCE & IMMUTABLE TRANSACTION LEDGER
# =====================================================================

class StockBalance(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='stock_balances')
    batch = models.ForeignKey(ProductBatch, on_delete=models.PROTECT, null=True, blank=True, related_name='stock_balances')
    location = models.ForeignKey(WarehouseLocation, on_delete=models.PROTECT, related_name='stock_balances')
    quantity = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ['product__name']
        constraints = [
            models.UniqueConstraint(fields=['product', 'batch', 'location'], name='unique_product_batch_location_balance')
        ]

    def __str__(self):
        return f"{self.product.sku} @ {self.location.code}: {self.quantity}"


class StockTransaction(TimeStampedModel):
    class TransactionType(models.TextChoices):
        RECEIVE = 'receive', 'Receive'
        RELEASE = 'release', 'Release'
        TRANSFER_IN = 'transfer_in', 'Transfer In'
        TRANSFER_OUT = 'transfer_out', 'Transfer Out'
        RETURN = 'return', 'Return'
        ADJUSTMENT_IN = 'adjustment_in', 'Adjustment In'
        ADJUSTMENT_OUT = 'adjustment_out', 'Adjustment Out'
        DAMAGE = 'damage', 'Damage'
        DISPOSAL = 'disposal', 'Disposal'

    reference_number = models.CharField(max_length=100, db_index=True)
    transaction_type = models.CharField(max_length=30, choices=TransactionType.choices)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='transactions')
    batch = models.ForeignKey(ProductBatch, on_delete=models.PROTECT, null=True, blank=True, related_name='transactions')
    location = models.ForeignKey(WarehouseLocation, on_delete=models.PROTECT, related_name='transactions')
    quantity = models.DecimalField(max_digits=14, decimal_places=2)
    balance_after = models.DecimalField(max_digits=14, decimal_places=2)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='stock_transactions')
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference_number} | {self.get_transaction_type_display()} | {self.product.sku}"


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=150)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} | {self.user} | {self.action}"


class Notification(models.Model):
    class Level(models.TextChoices):
        INFO = 'info', 'Info'
        WARNING = 'warning', 'Warning'
        DANGER = 'danger', 'Danger'

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    role_target = models.CharField(max_length=20, blank=True, help_text="Send to all users of this role instead of one user")
    message = models.CharField(max_length=255)
    level = models.CharField(max_length=10, choices=Level.choices, default=Level.INFO)
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.message


def log_action(user, action, description='', model_name='', object_id='', request=None):
    ip = request.META.get('REMOTE_ADDR') if request else None
    AuditLog.objects.create(user=user, action=action, model_name=model_name,
                             object_id=str(object_id), description=description, ip_address=ip)


def notify(message, level='info', link='', recipient=None, role_target=''):
    Notification.objects.create(recipient=recipient, role_target=role_target, message=message, level=level, link=link)


# =====================================================================
# RECEIVING
# =====================================================================

class Receiving(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        FOR_INSPECTION = 'for_inspection', 'For Inspection'
        PARTIALLY_ACCEPTED = 'partially_accepted', 'Partially Accepted'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'
        STORED = 'stored', 'Stored'

    reference_number = models.CharField(max_length=100, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='receivings')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='receivings')
    purchase_order = models.CharField(max_length=100, blank=True)
    delivery_receipt = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.DRAFT)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='receivings_done')
    inspected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='receivings_inspected')
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.reference_number


class ReceivingItem(models.Model):
    receiving = models.ForeignKey(Receiving, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    batch_number = models.CharField(max_length=100, blank=True)
    expiration_date = models.DateField(null=True, blank=True)
    location = models.ForeignKey(WarehouseLocation, on_delete=models.PROTECT)
    quantity_ordered = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    quantity_received = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    quantity_accepted = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    quantity_rejected = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_stored = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.product.sku} x{self.quantity_received}"


# =====================================================================
# STOCK TRANSFER
# =====================================================================

class StockTransfer(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        IN_TRANSIT = 'in_transit', 'In Transit'
        RECEIVED = 'received', 'Received'
        CANCELLED = 'cancelled', 'Cancelled'

    reference_number = models.CharField(max_length=100, unique=True)
    source_location = models.ForeignKey(WarehouseLocation, on_delete=models.PROTECT, related_name='transfers_out')
    destination_location = models.ForeignKey(WarehouseLocation, on_delete=models.PROTECT, related_name='transfers_in')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='transfers_requested')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='transfers_approved')
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.reference_number


class StockTransferItem(models.Model):
    transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    batch = models.ForeignKey(ProductBatch, on_delete=models.PROTECT, null=True, blank=True)
    quantity = models.DecimalField(max_digits=14, decimal_places=2)
    is_processed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.product.sku} x{self.quantity}"


# =====================================================================
# ITEM REQUEST & RELEASE
# =====================================================================

class ItemRequest(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        RELEASED = 'released', 'Released'
        PARTIALLY_RELEASED = 'partially_released', 'Partially Released'
        CANCELLED = 'cancelled', 'Cancelled'

    reference_number = models.CharField(max_length=100, unique=True)
    department = models.CharField(max_length=120)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='item_requests')
    purpose = models.TextField(blank=True)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.PENDING)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='item_requests_approved')
    approval_remarks = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.reference_number


class ItemRequestItem(models.Model):
    request = models.ForeignKey(ItemRequest, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity_requested = models.DecimalField(max_digits=14, decimal_places=2)
    quantity_released = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.product.sku} x{self.quantity_requested}"


class StockRelease(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        RELEASED = 'released', 'Released'
        CONFIRMED = 'confirmed', 'Confirmed'

    reference_number = models.CharField(max_length=100, unique=True)
    item_request = models.ForeignKey(ItemRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='releases')
    location = models.ForeignKey(WarehouseLocation, on_delete=models.PROTECT, related_name='releases')
    released_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='releases_done')
    released_to_department = models.CharField(max_length=120)
    recipient_name = models.CharField(max_length=150)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.reference_number


class StockReleaseItem(models.Model):
    release = models.ForeignKey(StockRelease, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    batch = models.ForeignKey(ProductBatch, on_delete=models.PROTECT, null=True, blank=True)
    quantity = models.DecimalField(max_digits=14, decimal_places=2)

    def __str__(self):
        return f"{self.product.sku} x{self.quantity}"


# =====================================================================
# RETURNS
# =====================================================================

class Return(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSED = 'processed', 'Processed'

    reference_number = models.CharField(max_length=100, unique=True)
    returned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='returns_filed')
    department = models.CharField(max_length=120, blank=True)
    location = models.ForeignKey(WarehouseLocation, on_delete=models.PROTECT, related_name='returns')
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.reference_number


class ReturnItem(models.Model):
    class Condition(models.TextChoices):
        GOOD = 'good', 'Good'
        USED = 'used', 'Used'
        DAMAGED = 'damaged', 'Damaged'
        FOR_REPAIR = 'for_repair', 'For Repair'
        CONDEMNED = 'condemned', 'Condemned'
        MISSING_PARTS = 'missing_parts', 'Missing Parts'

    return_doc = models.ForeignKey(Return, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    batch = models.ForeignKey(ProductBatch, on_delete=models.PROTECT, null=True, blank=True)
    quantity = models.DecimalField(max_digits=14, decimal_places=2)
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.GOOD)

    def __str__(self):
        return f"{self.product.sku} x{self.quantity}"


# =====================================================================
# INVENTORY COUNT
# =====================================================================

class InventoryCount(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        COUNTING = 'counting', 'Counting'
        FOR_REVIEW = 'for_review', 'For Review'
        APPROVED = 'approved', 'Approved'
        CLOSED = 'closed', 'Closed'

    reference_number = models.CharField(max_length=100, unique=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='inventory_counts')
    location = models.ForeignKey(WarehouseLocation, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_counts')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.OPEN)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='counts_created')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='counts_reviewed')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.reference_number


class InventoryCountItem(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        MATCHED = 'matched', 'Matched'
        FOR_INVESTIGATION = 'for_investigation', 'For Investigation'
        ADJUSTED = 'adjusted', 'Adjusted'

    count = models.ForeignKey(InventoryCount, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    batch = models.ForeignKey(ProductBatch, on_delete=models.PROTECT, null=True, blank=True)
    location = models.ForeignKey(WarehouseLocation, on_delete=models.PROTECT)
    expected_quantity = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    counted_quantity = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    counted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    counted_at = models.DateTimeField(null=True, blank=True)

    @property
    def variance(self):
        if self.counted_quantity is None:
            return None
        return self.counted_quantity - self.expected_quantity

    def __str__(self):
        return f"{self.product.sku} @ {self.location.code}"


# =====================================================================
# DAMAGE & DISPOSAL
# =====================================================================

class DamageReport(TimeStampedModel):
    class Status(models.TextChoices):
        REPORTED = 'reported', 'Reported'
        APPROVED = 'approved', 'Approved'
        DISPOSED = 'disposed', 'Disposed'
        REJECTED = 'rejected', 'Rejected'

    reference_number = models.CharField(max_length=100, unique=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='damage_reports')
    batch = models.ForeignKey(ProductBatch, on_delete=models.PROTECT, null=True, blank=True)
    location = models.ForeignKey(WarehouseLocation, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.TextField()
    photo = models.ImageField(upload_to='damage/', blank=True, null=True)
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='damage_reports_filed')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='damage_reports_approved')
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.REPORTED)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.reference_number


class Disposal(TimeStampedModel):
    class Method(models.TextChoices):
        SCRAP = 'scrap', 'Scrap'
        DONATE = 'donate', 'Donate'
        SELL = 'sell', 'Sell'
        RECYCLE = 'recycle', 'Recycle'
        RETURN_TO_SUPPLIER = 'return_to_supplier', 'Return to Supplier'
        DESTROY = 'destroy', 'Destroy'

    reference_number = models.CharField(max_length=100, unique=True)
    damage_report = models.ForeignKey(DamageReport, on_delete=models.SET_NULL, null=True, blank=True, related_name='disposals')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=25, choices=Method.choices)
    witnesses = models.CharField(max_length=255, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='disposals_approved')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.reference_number


