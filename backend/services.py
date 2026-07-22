"""
Central stock movement service.
Every function here is atomic, locks the relevant StockBalance row(s),
prevents negative stock, and writes an immutable StockTransaction record.
No view or module should ever edit StockBalance.quantity directly.
"""
import datetime
from django.db import transaction
from django.utils import timezone
from .models import StockBalance, StockTransaction, Product, notify


class InsufficientStockError(Exception):
    pass


def generate_reference(prefix):
    return f"{prefix}-{timezone.localdate():%Y%m%d}-{StockTransaction.objects.filter(created_at__date=timezone.localdate()).count() + 1:04d}"


def _get_or_create_balance(product, batch, location):
    balance, _ = StockBalance.objects.select_for_update().get_or_create(
        product=product, batch=batch, location=location, defaults={'quantity': 0}
    )
    return balance


def _check_low_stock(product):
    if product.reorder_level and product.total_stock <= product.reorder_level:
        notify(f"Low stock: {product.name} ({product.sku}) is at {product.total_stock} {product.unit.abbreviation}.",
               level='warning', role_target='manager', link=f'/inventory/products/{product.pk}/')
        if product.total_stock <= 0:
            notify(f"Out of stock: {product.name} ({product.sku}).", level='danger', role_target='manager')


@transaction.atomic
def receive_stock(product, location, quantity, user, batch=None, reference_number=None, remarks=''):
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")
    balance = _get_or_create_balance(product, batch, location)
    balance.quantity += quantity
    balance.save(update_fields=['quantity'])
    ref = reference_number or generate_reference('RCV')
    StockTransaction.objects.create(
        reference_number=ref, transaction_type=StockTransaction.TransactionType.RECEIVE,
        product=product, batch=batch, location=location, quantity=quantity,
        balance_after=balance.quantity, performed_by=user, remarks=remarks,
    )
    return balance


@transaction.atomic
def release_stock(product, location, quantity, user, batch=None, reference_number=None, remarks=''):
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")
    balance = _get_or_create_balance(product, batch, location)
    if balance.quantity < quantity:
        raise InsufficientStockError(f"Insufficient stock at {location}: available {balance.quantity}, requested {quantity}.")
    balance.quantity -= quantity
    balance.save(update_fields=['quantity'])
    ref = reference_number or generate_reference('REL')
    StockTransaction.objects.create(
        reference_number=ref, transaction_type=StockTransaction.TransactionType.RELEASE,
        product=product, batch=batch, location=location, quantity=-quantity,
        balance_after=balance.quantity, performed_by=user, remarks=remarks,
    )
    _check_low_stock(product)
    return balance


@transaction.atomic
def transfer_stock(product, source_location, destination_location, quantity, user, batch=None, reference_number=None, remarks=''):
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")
    if source_location_id_equal(source_location, destination_location):
        raise ValueError("Source and destination location must be different.")
    source_balance = _get_or_create_balance(product, batch, source_location)
    if source_balance.quantity < quantity:
        raise InsufficientStockError(f"Insufficient stock at {source_location}: available {source_balance.quantity}, requested {quantity}.")
    dest_balance = _get_or_create_balance(product, batch, destination_location)

    source_balance.quantity -= quantity
    source_balance.save(update_fields=['quantity'])
    dest_balance.quantity += quantity
    dest_balance.save(update_fields=['quantity'])

    ref = reference_number or generate_reference('TRF')
    StockTransaction.objects.create(
        reference_number=ref, transaction_type=StockTransaction.TransactionType.TRANSFER_OUT,
        product=product, batch=batch, location=source_location, quantity=-quantity,
        balance_after=source_balance.quantity, performed_by=user, remarks=remarks,
    )
    StockTransaction.objects.create(
        reference_number=ref, transaction_type=StockTransaction.TransactionType.TRANSFER_IN,
        product=product, batch=batch, location=destination_location, quantity=quantity,
        balance_after=dest_balance.quantity, performed_by=user, remarks=remarks,
    )
    return source_balance, dest_balance


def source_location_id_equal(a, b):
    return a.pk == b.pk


@transaction.atomic
def return_stock(product, location, quantity, user, batch=None, reference_number=None, remarks='', to_available=True):
    """to_available=False routes returned stock to a quarantine remark instead of usable balance."""
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")
    ref = reference_number or generate_reference('RET')
    if to_available:
        balance = _get_or_create_balance(product, batch, location)
        balance.quantity += quantity
        balance.save(update_fields=['quantity'])
        StockTransaction.objects.create(
            reference_number=ref, transaction_type=StockTransaction.TransactionType.RETURN,
            product=product, batch=batch, location=location, quantity=quantity,
            balance_after=balance.quantity, performed_by=user, remarks=remarks,
        )
        return balance
    else:
        # Quarantined / damaged / for-repair returns do not add to available balance,
        # but are still logged for the audit trail with quantity 0 net movement.
        StockTransaction.objects.create(
            reference_number=ref, transaction_type=StockTransaction.TransactionType.RETURN,
            product=product, batch=batch, location=location, quantity=0,
            balance_after=_get_or_create_balance(product, batch, location).quantity,
            performed_by=user, remarks=f"[Not added to available stock] {remarks}",
        )
        return None


@transaction.atomic
def adjust_stock(product, location, new_quantity, user, batch=None, reference_number=None, remarks=''):
    """Used after an inventory count is approved. new_quantity is the corrected physical count."""
    balance = _get_or_create_balance(product, batch, location)
    diff = new_quantity - balance.quantity
    if diff == 0:
        return balance
    ref = reference_number or generate_reference('ADJ')
    txn_type = StockTransaction.TransactionType.ADJUSTMENT_IN if diff > 0 else StockTransaction.TransactionType.ADJUSTMENT_OUT
    balance.quantity = new_quantity
    balance.save(update_fields=['quantity'])
    StockTransaction.objects.create(
        reference_number=ref, transaction_type=txn_type,
        product=product, batch=batch, location=location, quantity=diff,
        balance_after=balance.quantity, performed_by=user, remarks=remarks,
    )
    _check_low_stock(product)
    return balance


@transaction.atomic
def damage_stock(product, location, quantity, user, batch=None, reference_number=None, remarks=''):
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")
    balance = _get_or_create_balance(product, batch, location)
    if balance.quantity < quantity:
        raise InsufficientStockError(f"Cannot mark more damaged than available: available {balance.quantity}.")
    balance.quantity -= quantity
    balance.save(update_fields=['quantity'])
    ref = reference_number or generate_reference('DMG')
    StockTransaction.objects.create(
        reference_number=ref, transaction_type=StockTransaction.TransactionType.DAMAGE,
        product=product, batch=batch, location=location, quantity=-quantity,
        balance_after=balance.quantity, performed_by=user, remarks=remarks,
    )
    notify(f"Damage reported: {quantity} {product.unit.abbreviation} of {product.name} at {location}.",
           level='warning', role_target='manager')
    return balance


@transaction.atomic
def dispose_stock(product, quantity, user, location, batch=None, reference_number=None, remarks=''):
    """Disposal typically follows a damage report and does not touch available StockBalance again
    (the quantity was already deducted when damaged); this simply records the disposal transaction."""
    ref = reference_number or generate_reference('DSP')
    balance = _get_or_create_balance(product, batch, location)
    StockTransaction.objects.create(
        reference_number=ref, transaction_type=StockTransaction.TransactionType.DISPOSAL,
        product=product, batch=batch, location=location, quantity=0,
        balance_after=balance.quantity, performed_by=user, remarks=remarks,
    )
    return ref
