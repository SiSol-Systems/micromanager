try:
    from django.contrib.auth.forms import UsernameField
except ImportError:
    import unicodedata
    from django import forms
    class UsernameField(forms.CharField):
        def to_python(self, value):
            return unicodedata.normalize('NFKC', super(UsernameField, self).to_python(value))
    


try:
    from django.urls import reverse
except:
    from django.core.urlresolvers import reverse
