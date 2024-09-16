from .models import Log
from django import forms


class LogForm(forms.ModelForm):
    class Meta:
        model = Log
        exclude = [],
        widgets = {
            'school': forms.HiddenInput(),
            'student': forms.HiddenInput(),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': True}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'required': False}),
            'author': forms.TextInput(attrs={'class': 'form-control', 'required': False}),
            'pages': forms.NumberInput(attrs={'class': 'form-control', 'required': False}),
            'minutes': forms.NumberInput(attrs={'class': 'form-control', 'required': False}),
            'rating': forms.NumberInput(attrs={'class': 'form-control', 'required': False}),
            'comments': forms.Textarea(attrs={'class': 'form-control', 'required': False}),
        }

    def __init__(self, *args, **kwargs):
        super(LogForm, self).__init__(*args, **kwargs)
        self.fields['student'].required = True
