# records/forms.py
from django import forms
from .models import ArchiveBatch

class ArchiveBatchForm(forms.ModelForm):
    class Meta:
        model = ArchiveBatch
        fields = [
            'batch_type', 'reference_no', 'box_number', 'batch_no', 'batch_date',
            'grds_item', 'section', 'description', 'period_covered', 'latest_year',
            'years_as_of_count', 'retention_period_years', 'disposal_status_value',
            'scanning_status', 'location', 'linked_batch', 'remarks',
        ]
        widgets = {
            'location': forms.Select(attrs={'class': 'form-select'}),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add a comment...',
            }),
        }