from django.shortcuts import render, redirect
try:
    from django.urls import reverse
except:
    from django.core.urlresolvers import reverse

from django.contrib.auth import authenticate, login

from accounts.forms import LoginForm

from django.views.generic.edit import FormView
from django.utils.translation import ugettext as _

class LoginView(FormView):

    template_name = "accounts/login.html"
    form_class = LoginForm

    def form_valid(self, form):
        context = super(LoginView, self).get_context_data(**self.kwargs)
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user = authenticate(username=username, password=password)
        
        if user is not None:
            login(self.request, user)
            # Redirect to a success page.
            return redirect(reverse('micromanager_home'))
                
        context['error'] = _('User does not exist')
        return self.render_to_response(context)
        

from django.contrib.auth import logout

def logout_view(request):
    logout(request)
    return redirect(reverse('micromanager_home'))
