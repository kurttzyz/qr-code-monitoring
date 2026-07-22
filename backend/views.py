import csv
import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View

from .forms import (StyledAuthenticationForm, UserForm, WarehouseForm, WarehouseLocationForm,
                     CategoryForm, UnitForm, SupplierForm, ProductForm, ProductBatchForm, AssetForm,
                     ReceivingForm, ReceivingItemFormSet, StockTransferForm, StockTransferItemFormSet,
                     ItemRequestForm, ItemRequestItemFormSet, StockReleaseForm, StockReleaseItemFormSet,
                     ReturnForm, ReturnItemFormSet, InventoryCountForm, DamageReportForm, DisposalForm)
from .mixins import RoleRequiredMixin, NotReadOnlyMixin
from .models import (User, Warehouse, WarehouseLocation, Category, Unit, Supplier, Product,
                      ProductBatch, Asset, StockBalance, StockTransaction, AuditLog, Notification,
                      Receiving, ReceivingItem, StockTransfer, StockTransferItem,
                      ItemRequest, ItemRequestItem, StockRelease, StockReleaseItem,
                      Return, ReturnItem, InventoryCount, InventoryCountItem,
                      DamageReport, Disposal, log_action)
from .permissions import role_required, not_read_only, can_approve_required
from .qr_utils import qr_png_response, build_scan_url
from .services import (receive_stock, release_stock, transfer_stock, return_stock,
                        adjust_stock, damage_stock, dispose_stock, generate_reference,
                        InsufficientStockError)


# =====================================================================
# ACCOUNTS
# =====================================================================

class WarehouseLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True


@login_required
def logout_view(request):
    auth_logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('accounts:login')


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = UserForm(request.POST, instance=request.user)
        if not request.user.can_approve:
            form.fields['role'].disabled = True
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect('accounts:profile')
    else:
        form = UserForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})


@role_required('admin')
def user_list(request):
    users = User.objects.all().order_by('username')
    return render(request, 'accounts/user_list.html', {'users': users})


@role_required('admin')
def user_create(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "User created.")
            return redirect('accounts:user_list')
    else:
        form = UserForm()
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Add User'})


@role_required('admin')
def user_edit(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "User updated.")
            return redirect('accounts:user_list')
    else:
        form = UserForm(instance=user_obj)
    return render(request, 'accounts/user_form.html', {'form': form, 'title': f'Edit {user_obj.username}'})


# =====================================================================
# CORE: generic master-data CRUD
# =====================================================================

class MasterListView(LoginRequiredMixin, ListView):
    paginate_by = 25
    template_name = 'core/master_list.html'

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(self.search_q(q))
        return qs

    def search_q(self, q):
        return Q(pk__isnull=False)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(self.extra_ctx)
        return ctx


class WarehouseListView(MasterListView):
    model = Warehouse
    extra_ctx = {'title': 'Warehouses', 'add_url': 'core:warehouse_add', 'edit_url': 'core:warehouse_edit',
                 'delete_url': 'core:warehouse_delete', 'columns': ['code', 'name', 'address', 'is_active']}

    def search_q(self, q):
        return Q(code__icontains=q) | Q(name__icontains=q)


class WarehouseCreateView(NotReadOnlyMixin, RoleRequiredMixin, CreateView):
    model = Warehouse
    form_class = WarehouseForm
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('core:warehouse_list')
    extra_context = {'title': 'Add Warehouse'}
    allowed_roles = ('admin', 'manager')

    def form_valid(self, form):
        resp = super().form_valid(form)
        log_action(self.request.user, 'Created Warehouse', model_name='Warehouse', object_id=self.object.pk)
        messages.success(self.request, 'Warehouse created.')
        return resp

 
class WarehouseUpdateView(NotReadOnlyMixin, RoleRequiredMixin, UpdateView):
    model = Warehouse
    form_class = WarehouseForm
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('core:warehouse_list')
    extra_context = {'title': 'Edit Warehouse'}
    allowed_roles = ('admin', 'manager')

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, 'Warehouse updated.')
        return resp


class WarehouseDeleteView(NotReadOnlyMixin, RoleRequiredMixin, DeleteView):
    model = Warehouse
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('core:warehouse_list')
    allowed_roles = ('admin',)

    def form_valid(self, form):
        messages.success(self.request, 'Warehouse deleted.')
        return super().form_valid(form)


class CategoryListView(MasterListView):
    model = Category
    extra_ctx = {'title': 'Categories', 'add_url': 'core:category_add', 'edit_url': 'core:category_edit',
                 'delete_url': 'core:category_delete', 'columns': ['name', 'description']}

    def search_q(self, q):
        return Q(name__icontains=q)


class CategoryCreateView(NotReadOnlyMixin, RoleRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('core:category_list')
    extra_context = {'title': 'Add Category'}
    allowed_roles = ('admin', 'manager')


class CategoryUpdateView(NotReadOnlyMixin, RoleRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('core:category_list')
    extra_context = {'title': 'Edit Category'}
    allowed_roles = ('admin', 'manager')


class CategoryDeleteView(NotReadOnlyMixin, RoleRequiredMixin, DeleteView):
    model = Category
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('core:category_list')
    allowed_roles = ('admin',)


class UnitListView(MasterListView):
    model = Unit
    extra_ctx = {'title': 'Units', 'add_url': 'core:unit_add', 'edit_url': 'core:unit_edit',
                 'delete_url': 'core:unit_delete', 'columns': ['name', 'abbreviation']}

    def search_q(self, q):
        return Q(name__icontains=q)


class UnitCreateView(NotReadOnlyMixin, RoleRequiredMixin, CreateView):
    model = Unit
    form_class = UnitForm
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('core:unit_list')
    extra_context = {'title': 'Add Unit'}
    allowed_roles = ('admin', 'manager')


class UnitUpdateView(NotReadOnlyMixin, RoleRequiredMixin, UpdateView):
    model = Unit
    form_class = UnitForm
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('core:unit_list')
    extra_context = {'title': 'Edit Unit'}
    allowed_roles = ('admin', 'manager')


class UnitDeleteView(NotReadOnlyMixin, RoleRequiredMixin, DeleteView):
    model = Unit
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('core:unit_list')
    allowed_roles = ('admin',)


class SupplierListView(MasterListView):
    model = Supplier
    extra_ctx = {'title': 'Suppliers', 'add_url': 'core:supplier_add', 'edit_url': 'core:supplier_edit',
                 'delete_url': 'core:supplier_delete', 'columns': ['code', 'company_name', 'contact_person', 'phone', 'is_active']}

    def search_q(self, q):
        return Q(code__icontains=q) | Q(company_name__icontains=q)


class SupplierCreateView(NotReadOnlyMixin, RoleRequiredMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('core:supplier_list')
    extra_context = {'title': 'Add Supplier'}
    allowed_roles = ('admin', 'manager', 'staff')


class SupplierUpdateView(NotReadOnlyMixin, RoleRequiredMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('core:supplier_list')
    extra_context = {'title': 'Edit Supplier'}
    allowed_roles = ('admin', 'manager', 'staff')


class SupplierDeleteView(NotReadOnlyMixin, RoleRequiredMixin, DeleteView):
    model = Supplier
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('core:supplier_list')
    allowed_roles = ('admin',)


# ---------- Warehouse locations ----------

class LocationListView(LoginRequiredMixin, ListView):
    model = WarehouseLocation
    template_name = 'core/location_list.html'
    paginate_by = 25
    context_object_name = 'locations'

    def get_queryset(self):
        qs = WarehouseLocation.objects.select_related('warehouse', 'parent')
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q))
        wh = self.request.GET.get('warehouse')
        if wh:
            qs = qs.filter(warehouse_id=wh)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['warehouses'] = Warehouse.objects.filter(is_active=True)
        return ctx


class LocationCreateView(NotReadOnlyMixin, RoleRequiredMixin, CreateView):
    model = WarehouseLocation
    form_class = WarehouseLocationForm
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('core:location_list')
    extra_context = {'title': 'Add Location'}
    allowed_roles = ('admin', 'manager', 'staff')


class LocationUpdateView(NotReadOnlyMixin, RoleRequiredMixin, UpdateView):
    model = WarehouseLocation
    form_class = WarehouseLocationForm
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('core:location_list')
    extra_context = {'title': 'Edit Location'}
    allowed_roles = ('admin', 'manager', 'staff')


class LocationDeleteView(NotReadOnlyMixin, RoleRequiredMixin, DeleteView):
    model = WarehouseLocation
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('core:location_list')
    allowed_roles = ('admin',)


class LocationDetailView(LoginRequiredMixin, DetailView):
    model = WarehouseLocation
    template_name = 'core/location_detail.html'
    context_object_name = 'location'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['balances'] = self.object.stock_balances.select_related('product', 'batch').filter(quantity__gt=0)
        ctx['scan_url'] = build_scan_url(self.request, self.object.qr_token)
        return ctx


# ---------- Products ----------

class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'core/product_list.html'
    paginate_by = 25
    context_object_name = 'products'

    def get_queryset(self):
        qs = Product.objects.select_related('category', 'unit').annotate(stock=Sum('stock_balances__quantity'))
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(sku__icontains=q) | Q(name__icontains=q) | Q(barcode__icontains=q))
        cat = self.request.GET.get('category')
        if cat:
            qs = qs.filter(category_id=cat)
        low = self.request.GET.get('low')
        if low:
            qs = [p for p in qs if p.is_low_stock]
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = Category.objects.all()
        return ctx


class ProductCreateView(NotReadOnlyMixin, RoleRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('core:product_list')
    extra_context = {'title': 'Add Product'}
    allowed_roles = ('admin', 'manager', 'staff')

    def form_valid(self, form):
        resp = super().form_valid(form)
        log_action(self.request.user, 'Created Product', model_name='Product', object_id=self.object.pk)
        messages.success(self.request, 'Product created.')
        return resp


class ProductUpdateView(NotReadOnlyMixin, RoleRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('core:product_list')
    extra_context = {'title': 'Edit Product'}
    allowed_roles = ('admin', 'manager', 'staff')


class ProductDeleteView(NotReadOnlyMixin, RoleRequiredMixin, DeleteView):
    model = Product
    template_name = 'core/confirm_delete.html'
    success_url = reverse_lazy('core:product_list')
    allowed_roles = ('admin',)


class ProductDetailView(LoginRequiredMixin, DetailView):
    model = Product
    template_name = 'core/product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['balances'] = self.object.stock_balances.select_related('location', 'batch').filter(quantity__gt=0)
        ctx['batches'] = self.object.batches.all()[:20]
        ctx['transactions'] = self.object.transactions.select_related('location', 'performed_by')[:25]
        ctx['scan_url'] = build_scan_url(self.request, self.object.qr_token)
        return ctx


class ProductBatchListView(LoginRequiredMixin, ListView):
    model = ProductBatch
    template_name = 'core/batch_list.html'
    paginate_by = 25
    context_object_name = 'batches'

    def get_queryset(self):
        return ProductBatch.objects.select_related('product', 'supplier').order_by('-created_at')


class ProductBatchCreateView(NotReadOnlyMixin, RoleRequiredMixin, CreateView):
    model = ProductBatch
    form_class = ProductBatchForm
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('core:batch_list')
    extra_context = {'title': 'Add Batch'}
    allowed_roles = ('admin', 'manager', 'staff')


class ProductBatchUpdateView(NotReadOnlyMixin, RoleRequiredMixin, UpdateView):
    model = ProductBatch
    form_class = ProductBatchForm
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('core:batch_list')
    extra_context = {'title': 'Edit Batch'}
    allowed_roles = ('admin', 'manager', 'staff')


# ---------- Assets ----------

class AssetListView(LoginRequiredMixin, ListView):
    model = Asset
    template_name = 'core/asset_list.html'
    paginate_by = 25
    context_object_name = 'assets'

    def get_queryset(self):
        qs = Asset.objects.select_related('product', 'location', 'assigned_to')
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(asset_code__icontains=q) | Q(serial_number__icontains=q) | Q(product__name__icontains=q))
        return qs


class AssetCreateView(NotReadOnlyMixin, RoleRequiredMixin, CreateView):
    model = Asset
    form_class = AssetForm
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('core:asset_list')
    extra_context = {'title': 'Add Asset'}
    allowed_roles = ('admin', 'manager', 'staff')


class AssetUpdateView(NotReadOnlyMixin, RoleRequiredMixin, UpdateView):
    model = Asset
    form_class = AssetForm
    template_name = 'core/master_form.html'
    success_url = reverse_lazy('core:asset_list')
    extra_context = {'title': 'Edit Asset'}
    allowed_roles = ('admin', 'manager', 'staff')


class AssetDetailView(LoginRequiredMixin, DetailView):
    model = Asset
    template_name = 'core/asset_detail.html'
    context_object_name = 'asset'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['scan_url'] = build_scan_url(self.request, self.object.qr_token)
        return ctx


# ---------- QR: image, labels, scan resolver ----------

class QRImageView(LoginRequiredMixin, View):
    def get(self, request, token):
        data = build_scan_url(request, token)
        return qr_png_response(data)


# class ScanView(LoginRequiredMixin, View):
#     def get(self, request, token):
#         location = WarehouseLocation.objects.filter(qr_token=token).first()
#         if location:
#             return redirect('core:location_detail', pk=location.pk)
#         product = Product.objects.filter(qr_token=token).first()
#         if product:
#             return redirect('core:product_detail', pk=product.pk)
#         batch = ProductBatch.objects.filter(qr_token=token).first()
#         if batch:
#             return redirect('core:product_detail', pk=batch.product_id)
#         asset = Asset.objects.filter(qr_token=token).first()
#         if asset:
#             return redirect('core:asset_detail', pk=asset.pk)
#         raise Http404("QR code not recognized or has been deactivated.")

class ScanView(LoginRequiredMixin, View):
    def get(self, request, token):
        location = WarehouseLocation.objects.filter(qr_token=token).first()
        if location:
            return redirect('core:location_detail', pk=location.pk)
        product = Product.objects.filter(qr_token=token).first()
        if product:
            return redirect('core:product_detail', pk=product.pk)
        batch = ProductBatch.objects.filter(qr_token=token).first()
        if batch:
            return redirect('core:product_detail', pk=batch.product_id)
        asset = Asset.objects.filter(qr_token=token).first()
        if asset:
            return redirect('core:asset_detail', pk=asset.pk)
        archive_batch = ArchiveBatch.objects.filter(qr_token=token).first()
        if archive_batch:
            return redirect('records:archive_batch_detail', pk=archive_batch.pk)
        raise Http404("QR code not recognized or has been deactivated.")
 

class ScannerPageView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'core/scanner.html')


# =====================================================================
# OPERATIONS: RECEIVING
# =====================================================================

class ReceivingListView(ListView):
    model = Receiving
    template_name = 'operations/receiving_list.html'
    context_object_name = 'receivings'
    paginate_by = 25

    def get_queryset(self):
        return Receiving.objects.select_related('supplier', 'warehouse').all()


@not_read_only
@role_required('admin', 'manager', 'staff')
def receiving_create(request):
    if request.method == 'POST':
        form = ReceivingForm(request.POST)
        if form.is_valid():
            receiving = form.save(commit=False)
            receiving.reference_number = generate_reference('RCVD')
            receiving.received_by = request.user
            receiving.status = Receiving.Status.FOR_INSPECTION
            receiving.save()
            formset = ReceivingItemFormSet(request.POST, instance=receiving)
            if formset.is_valid():
                formset.save()
                messages.success(request, f"Receiving {receiving.reference_number} created. Proceed to inspect and store.")
                return redirect('operations:receiving_detail', pk=receiving.pk)
            messages.error(request, "Please fix the item errors below.")
        else:
            formset = ReceivingItemFormSet(request.POST)
    else:
        form = ReceivingForm()
        formset = ReceivingItemFormSet()
    return render(request, 'operations/receiving_form.html', {'form': form, 'formset': formset, 'title': 'New Receiving'})


def receiving_detail(request, pk):
    receiving = get_object_or_404(Receiving, pk=pk)
    return render(request, 'operations/receiving_detail.html', {'receiving': receiving})


@not_read_only
@role_required('admin', 'manager', 'staff')
def receiving_store(request, pk):
    receiving = get_object_or_404(Receiving, pk=pk)
    if request.method == 'POST':
        with transaction.atomic():
            for item in receiving.items.filter(is_stored=False):
                batch = None
                if item.batch_number:
                    batch, _ = ProductBatch.objects.get_or_create(
                        product=item.product, batch_number=item.batch_number,
                        defaults={'expiration_date': item.expiration_date}
                    )
                qty = item.quantity_received or item.quantity_ordered
                receive_stock(item.product, item.location, qty, request.user,
                               batch=batch, reference_number=receiving.reference_number,
                               remarks=f"Receiving {receiving.reference_number} from {receiving.supplier}")
                item.quantity_accepted = qty
                item.is_stored = True
                item.save(update_fields=['quantity_accepted', 'is_stored'])
            receiving.status = Receiving.Status.STORED
            receiving.inspected_by = request.user
            receiving.save(update_fields=['status', 'inspected_by'])
        log_action(request.user, 'Stored Receiving', model_name='Receiving', object_id=receiving.pk)
        messages.success(request, f"Receiving {receiving.reference_number} stored into inventory.")
    return redirect('operations:receiving_detail', pk=pk)


# =====================================================================
# OPERATIONS: STOCK TRANSFER
# =====================================================================

class TransferListView(ListView):
    model = StockTransfer
    template_name = 'operations/transfer_list.html'
    context_object_name = 'transfers'
    paginate_by = 25

    def get_queryset(self):
        return StockTransfer.objects.select_related('source_location', 'destination_location').all()


@not_read_only
@role_required('admin', 'manager', 'staff')
def transfer_create(request):
    if request.method == 'POST':
        form = StockTransferForm(request.POST)
        if form.is_valid():
            xfer = form.save(commit=False)
            xfer.reference_number = generate_reference('TRF')
            xfer.requested_by = request.user
            xfer.status = StockTransfer.Status.PENDING
            xfer.save()
            formset = StockTransferItemFormSet(request.POST, instance=xfer)
            if formset.is_valid():
                formset.save()
                messages.success(request, f"Transfer {xfer.reference_number} submitted for approval.")
                return redirect('operations:transfer_detail', pk=xfer.pk)
        else:
            formset = StockTransferItemFormSet(request.POST)
    else:
        form = StockTransferForm()
        formset = StockTransferItemFormSet()
    return render(request, 'operations/transfer_form.html', {'form': form, 'formset': formset, 'title': 'New Stock Transfer'})


def transfer_detail(request, pk):
    xfer = get_object_or_404(StockTransfer, pk=pk)
    return render(request, 'operations/transfer_detail.html', {'transfer': xfer})


@can_approve_required
def transfer_approve(request, pk):
    xfer = get_object_or_404(StockTransfer, pk=pk)
    if request.method == 'POST':
        xfer.status = StockTransfer.Status.APPROVED
        xfer.approved_by = request.user
        xfer.save(update_fields=['status', 'approved_by'])
        messages.success(request, f"Transfer {xfer.reference_number} approved.")
    return redirect('operations:transfer_detail', pk=pk)


@not_read_only
@role_required('admin', 'manager', 'staff')
def transfer_process(request, pk):
    xfer = get_object_or_404(StockTransfer, pk=pk)
    if xfer.status != StockTransfer.Status.APPROVED:
        messages.error(request, "Transfer must be approved before processing.")
        return redirect('operations:transfer_detail', pk=pk)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                for item in xfer.items.filter(is_processed=False):
                    transfer_stock(item.product, xfer.source_location, xfer.destination_location,
                                    item.quantity, request.user, batch=item.batch,
                                    reference_number=xfer.reference_number, remarks=xfer.remarks)
                    item.is_processed = True
                    item.save(update_fields=['is_processed'])
                xfer.status = StockTransfer.Status.RECEIVED
                xfer.save(update_fields=['status'])
            messages.success(request, f"Transfer {xfer.reference_number} completed. Stock moved.")
        except InsufficientStockError as e:
            messages.error(request, str(e))
    return redirect('operations:transfer_detail', pk=pk)


# =====================================================================
# OPERATIONS: ITEM REQUEST & RELEASE
# =====================================================================

class RequestListView(ListView):
    model = ItemRequest
    template_name = 'operations/request_list.html'
    context_object_name = 'requests'
    paginate_by = 25

    def get_queryset(self):
        return ItemRequest.objects.all()


@not_read_only
def request_create(request):
    if request.method == 'POST':
        form = ItemRequestForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.reference_number = generate_reference('REQ')
            req.requested_by = request.user
            req.save()
            formset = ItemRequestItemFormSet(request.POST, instance=req)
            if formset.is_valid():
                formset.save()
                messages.success(request, f"Request {req.reference_number} submitted.")
                return redirect('operations:request_detail', pk=req.pk)
        else:
            formset = ItemRequestItemFormSet(request.POST)
    else:
        form = ItemRequestForm(initial={'department': request.user.department})
        formset = ItemRequestItemFormSet()
    return render(request, 'operations/request_form.html', {'form': form, 'formset': formset, 'title': 'New Item Request'})


def request_detail(request, pk):
    req = get_object_or_404(ItemRequest, pk=pk)
    return render(request, 'operations/request_detail.html', {'req': req})


@can_approve_required
def request_review(request, pk, decision):
    req = get_object_or_404(ItemRequest, pk=pk)
    if request.method == 'POST':
        req.status = ItemRequest.Status.APPROVED if decision == 'approve' else ItemRequest.Status.REJECTED
        req.approved_by = request.user
        req.approval_remarks = request.POST.get('remarks', '')
        req.save()
        messages.success(request, f"Request {req.reference_number} {req.get_status_display().lower()}.")
    return redirect('operations:request_detail', pk=pk)


class ReleaseListView(ListView):
    model = StockRelease
    template_name = 'operations/release_list.html'
    context_object_name = 'releases'
    paginate_by = 25


@not_read_only
@role_required('admin', 'manager', 'staff')
def release_create(request, request_pk=None):
    item_request = get_object_or_404(ItemRequest, pk=request_pk) if request_pk else None
    if item_request and item_request.status not in (ItemRequest.Status.APPROVED, ItemRequest.Status.PARTIALLY_RELEASED):
        messages.error(request, "Only approved requests can be released.")
        return redirect('operations:request_detail', pk=request_pk)

    if request.method == 'POST':
        form = StockReleaseForm(request.POST)
        if form.is_valid():
            rel = form.save(commit=False)
            rel.reference_number = generate_reference('REL')
            rel.released_by = request.user
            rel.item_request = item_request
            rel.status = StockRelease.Status.RELEASED
            rel.save()
            formset = StockReleaseItemFormSet(request.POST, instance=rel)
            if formset.is_valid():
                try:
                    with transaction.atomic():
                        items = formset.save(commit=False)
                        for item in items:
                            item.release = rel
                            item.save()
                            release_stock(item.product, rel.location, item.quantity, request.user,
                                          batch=item.batch, reference_number=rel.reference_number,
                                          remarks=f"Released to {rel.released_to_department} ({rel.recipient_name})")
                        if item_request:
                            item_request.status = ItemRequest.Status.RELEASED
                            item_request.save(update_fields=['status'])
                    messages.success(request, f"Release {rel.reference_number} completed and stock deducted.")
                    return redirect('operations:release_detail', pk=rel.pk)
                except InsufficientStockError as e:
                    messages.error(request, str(e))
        else:
            formset = StockReleaseItemFormSet(request.POST)
    else:
        form = StockReleaseForm()
        formset = StockReleaseItemFormSet()
    return render(request, 'operations/release_form.html', {
        'form': form, 'formset': formset, 'title': 'New Stock Release', 'item_request': item_request})


def release_detail(request, pk):
    rel = get_object_or_404(StockRelease, pk=pk)
    return render(request, 'operations/release_detail.html', {'release': rel})


# =====================================================================
# OPERATIONS: RETURNS
# =====================================================================

class ReturnListView(ListView):
    model = Return
    template_name = 'operations/return_list.html'
    context_object_name = 'returns'
    paginate_by = 25


@not_read_only
def return_create(request):
    if request.method == 'POST':
        form = ReturnForm(request.POST)
        if form.is_valid():
            ret = form.save(commit=False)
            ret.reference_number = generate_reference('RET')
            ret.returned_by = request.user
            ret.save()
            formset = ReturnItemFormSet(request.POST, instance=ret)
            if formset.is_valid():
                with transaction.atomic():
                    items = formset.save(commit=False)
                    for item in items:
                        item.return_doc = ret
                        item.save()
                        goes_to_available = item.condition in ('good', 'used')
                        return_stock(item.product, ret.location, item.quantity, request.user,
                                     batch=item.batch, reference_number=ret.reference_number,
                                     remarks=f"Return, condition: {item.get_condition_display()}",
                                     to_available=goes_to_available)
                    ret.status = Return.Status.PROCESSED
                    ret.save(update_fields=['status'])
                messages.success(request, f"Return {ret.reference_number} processed.")
                return redirect('operations:return_detail', pk=ret.pk)
        else:
            formset = ReturnItemFormSet(request.POST)
    else:
        form = ReturnForm()
        formset = ReturnItemFormSet()
    return render(request, 'operations/return_form.html', {'form': form, 'formset': formset, 'title': 'New Return'})


def return_detail(request, pk):
    ret = get_object_or_404(Return, pk=pk)
    return render(request, 'operations/return_detail.html', {'ret': ret})


# =====================================================================
# OPERATIONS: INVENTORY COUNT
# =====================================================================

class CountListView(ListView):
    model = InventoryCount
    template_name = 'operations/count_list.html'
    context_object_name = 'counts'
    paginate_by = 25


@not_read_only
@role_required('admin', 'manager')
def count_create(request):
    if request.method == 'POST':
        form = InventoryCountForm(request.POST)
        if form.is_valid():
            count = form.save(commit=False)
            count.reference_number = generate_reference('CNT')
            count.created_by = request.user
            count.status = InventoryCount.Status.COUNTING
            count.save()
            balances = StockBalance.objects.select_related('product', 'location').filter(
                location__warehouse=count.warehouse, quantity__gt=0)
            if count.location:
                balances = balances.filter(location=count.location)
            if count.category:
                balances = balances.filter(product__category=count.category)
            items = [InventoryCountItem(count=count, product=b.product, batch=b.batch,
                                         location=b.location, expected_quantity=b.quantity)
                     for b in balances]
            InventoryCountItem.objects.bulk_create(items)
            messages.success(request, f"Count session {count.reference_number} created with {len(items)} line(s) to count.")
            return redirect('operations:count_detail', pk=count.pk)
    else:
        form = InventoryCountForm()
    return render(request, 'operations/count_form.html', {'form': form, 'title': 'New Inventory Count'})


def count_detail(request, pk):
    count = get_object_or_404(InventoryCount, pk=pk)
    return render(request, 'operations/count_detail.html', {'count': count})


@not_read_only
@role_required('admin', 'manager', 'staff')
def count_entry(request, pk, item_pk):
    count = get_object_or_404(InventoryCount, pk=pk)
    item = get_object_or_404(InventoryCountItem, pk=item_pk, count=count)
    if request.method == 'POST':
        qty = request.POST.get('counted_quantity')
        try:
            item.counted_quantity = Decimal(qty)
        except Exception:
            messages.error(request, "Enter a valid number.")
            return redirect('operations:count_detail', pk=pk)
        item.counted_by = request.user
        item.counted_at = timezone.now()
        item.status = InventoryCountItem.Status.MATCHED if item.variance == 0 else InventoryCountItem.Status.FOR_INVESTIGATION
        item.save()
        messages.success(request, f"Count recorded for {item.product.sku}. Variance: {item.variance}")
    return redirect('operations:count_detail', pk=pk)


@can_approve_required
def count_approve(request, pk):
    count = get_object_or_404(InventoryCount, pk=pk)
    if request.method == 'POST':
        with transaction.atomic():
            for item in count.items.exclude(status=InventoryCountItem.Status.PENDING):
                if item.counted_quantity is not None and item.variance != 0:
                    adjust_stock(item.product, item.location, item.counted_quantity, request.user,
                                 batch=item.batch, reference_number=count.reference_number,
                                 remarks=f"Inventory count {count.reference_number} adjustment")
                    item.status = InventoryCountItem.Status.ADJUSTED
                    item.save(update_fields=['status'])
            count.status = InventoryCount.Status.CLOSED
            count.reviewed_by = request.user
            count.completed_at = timezone.now()
            count.save(update_fields=['status', 'reviewed_by', 'completed_at'])
        messages.success(request, f"Count {count.reference_number} approved and adjustments applied.")
    return redirect('operations:count_detail', pk=pk)


# =====================================================================
# OPERATIONS: DAMAGE & DISPOSAL
# =====================================================================

class DamageListView(ListView):
    model = DamageReport
    template_name = 'operations/damage_list.html'
    context_object_name = 'reports'
    paginate_by = 25


@not_read_only
def damage_create(request):
    if request.method == 'POST':
        form = DamageReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.reference_number = generate_reference('DMG')
            report.reported_by = request.user
            report.save()
            messages.success(request, f"Damage report {report.reference_number} filed. Awaiting manager approval.")
            return redirect('operations:damage_detail', pk=report.pk)
    else:
        form = DamageReportForm()
    return render(request, 'operations/damage_form.html', {'form': form, 'title': 'Report Damage'})


def damage_detail(request, pk):
    report = get_object_or_404(DamageReport, pk=pk)
    return render(request, 'operations/damage_detail.html', {'report': report})


@can_approve_required
def damage_approve(request, pk):
    report = get_object_or_404(DamageReport, pk=pk)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                damage_stock(report.product, report.location, report.quantity, request.user,
                             batch=report.batch, reference_number=report.reference_number,
                             remarks=report.reason)
                report.status = DamageReport.Status.APPROVED
                report.approved_by = request.user
                report.save(update_fields=['status', 'approved_by'])
            messages.success(request, f"Damage report {report.reference_number} approved and stock deducted.")
        except InsufficientStockError as e:
            messages.error(request, str(e))
    return redirect('operations:damage_detail', pk=pk)


class DisposalListView(ListView):
    model = Disposal
    template_name = 'operations/disposal_list.html'
    context_object_name = 'disposals'
    paginate_by = 25


@can_approve_required
def disposal_create(request):
    if request.method == 'POST':
        form = DisposalForm(request.POST)
        if form.is_valid():
            disposal = form.save(commit=False)
            disposal.reference_number = generate_reference('DSP')
            disposal.approved_by = request.user
            disposal.save()
            location = disposal.damage_report.location if disposal.damage_report else None
            if location:
                dispose_stock(disposal.product, disposal.quantity, request.user, location,
                               reference_number=disposal.reference_number,
                               remarks=f"Disposal via {disposal.get_method_display()}")
            if disposal.damage_report:
                disposal.damage_report.status = DamageReport.Status.DISPOSED
                disposal.damage_report.save(update_fields=['status'])
            messages.success(request, f"Disposal {disposal.reference_number} recorded.")
            return redirect('operations:disposal_list')
    else:
        form = DisposalForm()
    return render(request, 'operations/disposal_form.html', {'form': form, 'title': 'Record Disposal'})


# =====================================================================
# DASHBOARD
# =====================================================================
 
from records.models import ArchiveBatch, DisposalRequest  # add near your other imports
 
 
@login_required
def home(request):
    today = timezone.localdate()
    products = Product.objects.filter(is_active=True)
    total_products = products.count()
    total_available = StockBalance.objects.aggregate(t=Sum('quantity'))['t'] or 0
 
    low_stock = [p for p in products if p.reorder_level and p.is_low_stock and not p.is_out_of_stock]
    out_of_stock = [p for p in products if p.is_out_of_stock]
 
    expiring_batches = ProductBatch.objects.filter(
        expiration_date__isnull=False,
        expiration_date__lte=today + datetime.timedelta(days=30),
        expiration_date__gte=today,
    ).select_related('product')
 
    received_today = StockTransaction.objects.filter(
        transaction_type='receive', created_at__date=today).aggregate(t=Sum('quantity'))['t'] or 0
    released_today = StockTransaction.objects.filter(
        transaction_type='release', created_at__date=today).aggregate(t=Sum('quantity'))['t'] or 0
 
    pending_requests = ItemRequest.objects.filter(status='pending').count()
    pending_transfers = StockTransfer.objects.filter(status='pending').count()
    pending_damage = DamageReport.objects.filter(status='reported').count()
 
    recent_transactions = StockTransaction.objects.select_related('product', 'location', 'performed_by')[:10]
 
    days = [today - datetime.timedelta(days=i) for i in range(6, -1, -1)]
    chart_labels = [d.strftime('%b %d') for d in days]
    chart_received, chart_released = [], []
    for d in days:
        chart_received.append(float(StockTransaction.objects.filter(transaction_type='receive', created_at__date=d).aggregate(t=Sum('quantity'))['t'] or 0))
        chart_released.append(float(abs(StockTransaction.objects.filter(transaction_type='release', created_at__date=d).aggregate(t=Sum('quantity'))['t'] or 0)))
 
    top_categories = (StockBalance.objects.values('product__category__name')
                       .annotate(total=Sum('quantity')).order_by('-total')[:6])
 
    # --- Records (NAP-GRDS) additions ---
    total_archive_batches = ArchiveBatch.objects.count()
    eligible_for_disposal = ArchiveBatch.objects.filter(
        batch_type=ArchiveBatch.BatchType.ARCHIVING,
        disposal_status_value__gte=0,
    )
    eligible_for_disposal_count = eligible_for_disposal.count()
    pending_disposal_requests = DisposalRequest.objects.filter(
        status__in=[DisposalRequest.Status.DRAFT, DisposalRequest.Status.SUBMITTED]
    ).count()
    recent_batches = ArchiveBatch.objects.select_related('grds_item', 'section').order_by('-created_at')[:6]
 
    context = {
        'total_products': total_products,
        'total_available': total_available,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'expiring_batches': expiring_batches,
        'received_today': received_today,
        'released_today': abs(released_today),
        'pending_requests': pending_requests,
        'pending_transfers': pending_transfers,
        'pending_damage': pending_damage,
        'recent_transactions': recent_transactions,
        'chart_labels': chart_labels,
        'chart_received': chart_received,
        'chart_released': chart_released,
        'top_categories': list(top_categories),
        'warehouses': Warehouse.objects.filter(is_active=True).count(),
        # records additions
        'total_archive_batches': total_archive_batches,
        'eligible_for_disposal_count': eligible_for_disposal_count,
        'pending_disposal_requests': pending_disposal_requests,
        'recent_batches': recent_batches,
    }
    return render(request, 'dashboard/home.html', context)

@login_required
def notifications_all(request):
    qs = Notification.objects.filter(Q(recipient=request.user) | Q(role_target=request.user.role)).order_by('-created_at')
    return render(request, 'dashboard/notifications.html', {'notifications': qs})


@login_required
def notification_mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk)
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    return redirect(notif.link or 'dashboard:notifications')


@login_required
def audit_log(request):
    logs = AuditLog.objects.select_related('user')[:200]
    return render(request, 'dashboard/audit_log.html', {'logs': logs})


@login_required
def reports_home(request):
    return render(request, 'dashboard/reports.html')


@login_required
def report_stock(request):
    balances = StockBalance.objects.select_related('product', 'location', 'batch').filter(quantity__gt=0)
    wh = request.GET.get('warehouse')
    if wh:
        balances = balances.filter(location__warehouse_id=wh)
    if request.GET.get('export') == 'csv':
        return _csv_export('current_stock_report.csv',
                            ['SKU', 'Product', 'Batch', 'Location', 'Quantity'],
                            [[b.product.sku, b.product.name, b.batch.batch_number if b.batch else '', str(b.location), b.quantity] for b in balances])
    return render(request, 'dashboard/report_stock.html', {'balances': balances, 'warehouses': Warehouse.objects.all()})


@login_required
def report_movement(request):
    txns = StockTransaction.objects.select_related('product', 'location', 'performed_by')
    ttype = request.GET.get('type')
    if ttype:
        txns = txns.filter(transaction_type=ttype)
    date_from = request.GET.get('from')
    date_to = request.GET.get('to')
    if date_from:
        txns = txns.filter(created_at__date__gte=date_from)
    if date_to:
        txns = txns.filter(created_at__date__lte=date_to)
    txns = txns[:500]
    if request.GET.get('export') == 'csv':
        return _csv_export('stock_movement_ledger.csv',
                            ['Date', 'Reference', 'Type', 'SKU', 'Product', 'Location', 'Quantity', 'Balance After', 'By'],
                            [[t.created_at.strftime('%Y-%m-%d %H:%M'), t.reference_number, t.get_transaction_type_display(),
                              t.product.sku, t.product.name, str(t.location), t.quantity, t.balance_after, str(t.performed_by)]
                             for t in txns])
    return render(request, 'dashboard/report_movement.html', {
        'transactions': txns, 'types': StockTransaction.TransactionType.choices})


@login_required
def report_low_stock(request):
    products = [p for p in Product.objects.filter(is_active=True) if p.is_low_stock]
    if request.GET.get('export') == 'csv':
        return _csv_export('low_stock_report.csv', ['SKU', 'Product', 'Total Stock', 'Reorder Level'],
                            [[p.sku, p.name, p.total_stock, p.reorder_level] for p in products])
    return render(request, 'dashboard/report_low_stock.html', {'products': products})


@login_required
def report_expiration(request):
    today = timezone.localdate()
    batches = ProductBatch.objects.select_related('product').filter(
        expiration_date__isnull=False).order_by('expiration_date')
    if request.GET.get('export') == 'csv':
        return _csv_export('expiration_report.csv', ['SKU', 'Product', 'Batch', 'Expiration Date'],
                            [[b.product.sku, b.product.name, b.batch_number, b.expiration_date] for b in batches])
    return render(request, 'dashboard/report_expiration.html', {'batches': batches, 'today': today})


def _csv_export(filename, header, rows):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    return response
