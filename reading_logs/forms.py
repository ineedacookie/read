from .models import Log
from django import forms
from read.utils.form_helpers import apply_form_control_styling


class LogForm(forms.ModelForm):
    class Meta:
        model = Log
        exclude = []
        widgets = {
            'school': forms.HiddenInput(),
            'student': forms.HiddenInput(),
            'date': forms.DateInput(attrs={'type': 'date', 'required': True}),
            'title': forms.TextInput(attrs={'required': False}),
            'author': forms.TextInput(attrs={'required': False}),
            'pages': forms.NumberInput(attrs={'required': False}),
            'minutes': forms.NumberInput(attrs={'required': False}),
            'rating': forms.NumberInput(attrs={'required': False}),
            'comments': forms.Textarea(attrs={'required': False}),
        }

    def __init__(self, *args, **kwargs):
        super(LogForm, self).__init__(*args, **kwargs)
        # Apply common form styling using helper function
        apply_form_control_styling(self)
        self.fields['student'].required = True
