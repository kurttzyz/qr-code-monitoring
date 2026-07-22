from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.forms import inlineformset_factory
from .models import (User, Warehouse, WarehouseLocation, Category, Unit, Supplier, Product,
                      ProductBatch, Asset, Receiving, ReceivingItem, StockTransfer, StockTransferItem,
                      ItemRequest, ItemRequestItem, StockRelease, StockReleaseItem,
                      Return, ReturnItem, InventoryCount, InventoryCountItem,
                      DamageReport, Disposal)

BASE = {'class': 'form-control'}
SEL = {'class': 'form-select'}


# ---------------- Accounts ----------------

class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username', 'autofocus': True})
        self.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})


class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False, help_text="Leave blank to keep current password.")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'employee_id',
                  'department', 'phone', 'is_active_employee']
        widgets = {f: forms.TextInput(attrs=BASE) for f in
                   ['username', 'first_name', 'last_name', 'email', 'employee_id', 'department', 'phone']}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].widget.attrs.update({'class': 'form-select'})
        self.fields['is_active_employee'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['password'].widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
        user = super().save(commit=False)
        pwd = self.cleaned_data.get('password')
        if pwd:
            user.set_password(pwd)
        if commit:
            user.save()
        return user


# ---------------- Master data ----------------

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['code', 'name', 'address', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs=BASE), 'name': forms.TextInput(attrs=BASE),
            'address': forms.Textarea(attrs={**BASE, 'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class WarehouseLocationForm(forms.ModelForm):
    class Meta:
        model = WarehouseLocation
        fields = ['warehouse', 'code', 'name', 'location_type', 'parent', 'is_active']
        widgets = {
            'warehouse': forms.Select(attrs=SEL), 'code': forms.TextInput(attrs=BASE),
            'name': forms.TextInput(attrs=BASE), 'location_type': forms.Select(attrs=SEL),
            'parent': forms.Select(attrs=SEL), 'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {'name': forms.TextInput(attrs=BASE), 'description': forms.Textarea(attrs={**BASE, 'rows': 2})}


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = ['name', 'abbreviation']
        widgets = {'name': forms.TextInput(attrs=BASE), 'abbreviation': forms.TextInput(attrs=BASE)}


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['code', 'company_name', 'contact_person', 'email', 'phone', 'address', 'tax_id', 'is_active']
        widgets = {f: forms.TextInput(attrs=BASE) for f in
                   ['code', 'company_name', 'contact_person', 'email', 'phone', 'tax_id']}
        widgets['address'] = forms.Textarea(attrs={**BASE, 'rows': 2})
        widgets['is_active'] = forms.CheckboxInput(attrs={'class': 'form-check-input'})


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['sku', 'name', 'description', 'category', 'unit', 'tracking_type', 'brand',
                  'barcode', 'image', 'minimum_stock', 'maximum_stock', 'reorder_level', 'is_active']
        widgets = {
            'sku': forms.TextInput(attrs=BASE), 'name': forms.TextInput(attrs=BASE),
            'description': forms.Textarea(attrs={**BASE, 'rows': 2}),
            'category': forms.Select(attrs=SEL), 'unit': forms.Select(attrs=SEL),
            'tracking_type': forms.Select(attrs=SEL), 'brand': forms.TextInput(attrs=BASE),
            'barcode': forms.TextInput(attrs=BASE), 'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'minimum_stock': forms.NumberInput(attrs=BASE), 'maximum_stock': forms.NumberInput(attrs=BASE),
            'reorder_level': forms.NumberInput(attrs=BASE),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ProductBatchForm(forms.ModelForm):
    class Meta:
        model = ProductBatch
        fields = ['product', 'batch_number', 'manufacturing_date', 'expiration_date', 'supplier']
        widgets = {
            'product': forms.Select(attrs=SEL), 'batch_number': forms.TextInput(attrs=BASE),
            'manufacturing_date': forms.DateInput(attrs={**BASE, 'type': 'date'}),
            'expiration_date': forms.DateInput(attrs={**BASE, 'type': 'date'}),
            'supplier': forms.Select(attrs=SEL),
        }


class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = ['asset_code', 'product', 'serial_number', 'location', 'condition', 'status', 'assigned_to', 'notes']
        widgets = {
            'asset_code': forms.TextInput(attrs=BASE), 'product': forms.Select(attrs=SEL),
            'serial_number': forms.TextInput(attrs=BASE), 'location': forms.Select(attrs=SEL),
            'condition': forms.Select(attrs=SEL), 'status': forms.Select(attrs=SEL),
            'assigned_to': forms.Select(attrs=SEL), 'notes': forms.Textarea(attrs={**BASE, 'rows': 2}),
        }


# ---------------- Operations ----------------

class ReceivingForm(forms.ModelForm):
    class Meta:
        model = Receiving
        fields = ['supplier', 'warehouse', 'purchase_order', 'delivery_receipt', 'remarks']
        widgets = {
            'supplier': forms.Select(attrs=SEL), 'warehouse': forms.Select(attrs=SEL),
            'purchase_order': forms.TextInput(attrs=BASE), 'delivery_receipt': forms.TextInput(attrs=BASE),
            'remarks': forms.Textarea(attrs={**BASE, 'rows': 2}),
        }


class ReceivingItemForm(forms.ModelForm):
    class Meta:
        model = ReceivingItem
        fields = ['product', 'batch_number', 'expiration_date', 'location', 'quantity_ordered',
                  'quantity_received', 'unit_cost']
        widgets = {
            'product': forms.Select(attrs=SEL), 'batch_number': forms.TextInput(attrs=BASE),
            'expiration_date': forms.DateInput(attrs={**BASE, 'type': 'date'}),
            'location': forms.Select(attrs=SEL),
            'quantity_ordered': forms.NumberInput(attrs=BASE), 'quantity_received': forms.NumberInput(attrs=BASE),
            'unit_cost': forms.NumberInput(attrs=BASE),
        }


ReceivingItemFormSet = inlineformset_factory(Receiving, ReceivingItem, form=ReceivingItemForm, extra=3, can_delete=True)


class StockTransferForm(forms.ModelForm):
    class Meta:
        model = StockTransfer
        fields = ['source_location', 'destination_location', 'remarks']
        widgets = {'source_location': forms.Select(attrs=SEL), 'destination_location': forms.Select(attrs=SEL),
                   'remarks': forms.Textarea(attrs={**BASE, 'rows': 2})}


class StockTransferItemForm(forms.ModelForm):
    class Meta:
        model = StockTransferItem
        fields = ['product', 'batch', 'quantity']
        widgets = {'product': forms.Select(attrs=SEL), 'batch': forms.Select(attrs=SEL), 'quantity': forms.NumberInput(attrs=BASE)}


StockTransferItemFormSet = inlineformset_factory(StockTransfer, StockTransferItem, form=StockTransferItemForm, extra=3, can_delete=True)


class ItemRequestForm(forms.ModelForm):
    class Meta:
        model = ItemRequest
        fields = ['department', 'purpose']
        widgets = {'department': forms.TextInput(attrs=BASE), 'purpose': forms.Textarea(attrs={**BASE, 'rows': 2})}


class ItemRequestItemForm(forms.ModelForm):
    class Meta:
        model = ItemRequestItem
        fields = ['product', 'quantity_requested']
        widgets = {'product': forms.Select(attrs=SEL), 'quantity_requested': forms.NumberInput(attrs=BASE)}


ItemRequestItemFormSet = inlineformset_factory(ItemRequest, ItemRequestItem, form=ItemRequestItemForm, extra=3, can_delete=True)


class StockReleaseForm(forms.ModelForm):
    class Meta:
        model = StockRelease
        fields = ['item_request', 'location', 'released_to_department', 'recipient_name', 'remarks']
        widgets = {'item_request': forms.Select(attrs=SEL), 'location': forms.Select(attrs=SEL),
                   'released_to_department': forms.TextInput(attrs=BASE), 'recipient_name': forms.TextInput(attrs=BASE),
                   'remarks': forms.Textarea(attrs={**BASE, 'rows': 2})}


class StockReleaseItemForm(forms.ModelForm):
    class Meta:
        model = StockReleaseItem
        fields = ['product', 'batch', 'quantity']
        widgets = {'product': forms.Select(attrs=SEL), 'batch': forms.Select(attrs=SEL), 'quantity': forms.NumberInput(attrs=BASE)}


StockReleaseItemFormSet = inlineformset_factory(StockRelease, StockReleaseItem, form=StockReleaseItemForm, extra=3, can_delete=True)


class ReturnForm(forms.ModelForm):
    class Meta:
        model = Return
        fields = ['department', 'location', 'reason']
        widgets = {'department': forms.TextInput(attrs=BASE), 'location': forms.Select(attrs=SEL),
                   'reason': forms.Textarea(attrs={**BASE, 'rows': 2})}


class ReturnItemForm(forms.ModelForm):
    class Meta:
        model = ReturnItem
        fields = ['product', 'batch', 'quantity', 'condition']
        widgets = {'product': forms.Select(attrs=SEL), 'batch': forms.Select(attrs=SEL),
                   'quantity': forms.NumberInput(attrs=BASE), 'condition': forms.Select(attrs=SEL)}


ReturnItemFormSet = inlineformset_factory(Return, ReturnItem, form=ReturnItemForm, extra=3, can_delete=True)


class InventoryCountForm(forms.ModelForm):
    class Meta:
        model = InventoryCount
        fields = ['warehouse', 'location', 'category', 'notes']
        widgets = {'warehouse': forms.Select(attrs=SEL), 'location': forms.Select(attrs=SEL),
                   'category': forms.Select(attrs=SEL), 'notes': forms.Textarea(attrs={**BASE, 'rows': 2})}


class InventoryCountEntryForm(forms.ModelForm):
    class Meta:
        model = InventoryCountItem
        fields = ['counted_quantity']
        widgets = {'counted_quantity': forms.NumberInput(attrs=BASE)}


class DamageReportForm(forms.ModelForm):
    class Meta:
        model = DamageReport
        fields = ['product', 'batch', 'location', 'quantity', 'reason', 'photo']
        widgets = {'product': forms.Select(attrs=SEL), 'batch': forms.Select(attrs=SEL),
                   'location': forms.Select(attrs=SEL), 'quantity': forms.NumberInput(attrs=BASE),
                   'reason': forms.Textarea(attrs={**BASE, 'rows': 2}), 'photo': forms.ClearableFileInput(attrs={'class': 'form-control'})}


class DisposalForm(forms.ModelForm):
    class Meta:
        model = Disposal
        fields = ['damage_report', 'product', 'quantity', 'method', 'witnesses']
        widgets = {'damage_report': forms.Select(attrs=SEL), 'product': forms.Select(attrs=SEL),
                   'quantity': forms.NumberInput(attrs=BASE), 'method': forms.Select(attrs=SEL),
                   'witnesses': forms.TextInput(attrs=BASE)}
