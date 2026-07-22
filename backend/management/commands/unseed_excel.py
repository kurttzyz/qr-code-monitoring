"""
Management command: unseed_excel

Deletes everything seed_excel.py created, by looking for the markers it
stamped on every record ("Imported from Excel" in remarks/purpose).

INSTALL
-------
Put this file at:  backend/management/commands/unseed_excel.py
(same folder as seed_excel.py)

USAGE
-----
    python manage.py unseed_excel --dry-run     # see counts, deletes nothing
    python manage.py unseed_excel                # actually deletes

    # also remove the catalog (Product/Category/Unit) and the placeholder
    # Warehouse/WarehouseLocation/Supplier/User that seed_excel.py created:
    python manage.py unseed_excel --full
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

# >>> EDIT: same app name you used in seed_excel.py
from backend.models import (  # noqa
    Category, Unit, Product, Supplier, Warehouse, WarehouseLocation,
    ItemRequest, Receiving, StockRelease,
)

User = get_user_model()

IMPORT_MARKER = 'Imported from Excel'


class Command(BaseCommand):
    help = "Undo seed_excel.py: deletes ItemRequests, Receivings, and StockReleases it created."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                             help="Report counts without deleting anything.")
        parser.add_argument('--full', action='store_true',
                             help="Also delete the Product/Category/Unit catalog and the "
                                  "placeholder Warehouse/WarehouseLocation/Supplier/User "
                                  "that seed_excel.py created. Skip this if you've since "
                                  "created real data that references any of them.")

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        full = options['full']

        with transaction.atomic():
            requests_qs = ItemRequest.objects.filter(purpose__startswith=IMPORT_MARKER)
            receivings_qs = Receiving.objects.filter(remarks__startswith=IMPORT_MARKER)
            releases_qs = StockRelease.objects.filter(remarks__startswith=IMPORT_MARKER)

            req_count = requests_qs.count()
            rcv_count = receivings_qs.count()
            rel_count = releases_qs.count()

            self.stdout.write(f"ItemRequests to delete:  {req_count} (items cascade automatically)")
            self.stdout.write(f"Receivings to delete:    {rcv_count} (items cascade automatically)")
            self.stdout.write(f"StockReleases to delete: {rel_count} (items cascade automatically)")

            requests_qs.delete()
            receivings_qs.delete()
            releases_qs.delete()

            if full:
                # Products/Categories/Units carry no marker of their own (they're just
                # catalog rows), so this assumes a *fresh* import with nothing else
                # depending on them yet. If any Product is still referenced by a
                # request/receiving/release you kept, PROTECT will stop the delete
                # and tell you which one.
                prod_count = Product.objects.count()
                cat_count = Category.objects.count()
                unit_count = Unit.objects.count()
                self.stdout.write(f"Products to delete (--full): {prod_count}")
                self.stdout.write(f"Categories to delete (--full): {cat_count}")
                self.stdout.write(f"Units to delete (--full): {unit_count}")

                Product.objects.all().delete()
                Category.objects.all().delete()
                Unit.objects.all().delete()

                WarehouseLocation.objects.filter(code='MAIN-01').delete()
                Warehouse.objects.filter(code='MAIN').delete()
                Supplier.objects.filter(code='UNSPEC').delete()
                User.objects.filter(username='excel_import').delete()
                self.stdout.write("Deleted placeholder Warehouse/WarehouseLocation/Supplier/User too.")

            if dry_run:
                self.stdout.write(self.style.WARNING("--dry-run set: rolling back, nothing was actually deleted."))
                transaction.set_rollback(True)
            else:
                self.stdout.write(self.style.SUCCESS("Done. Import undone."))