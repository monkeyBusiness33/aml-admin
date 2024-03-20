from django.shortcuts import render, redirect
from .forms import ContactUsForm
from django.views.generic.edit import FormView
import datetime
from django.contrib import messages
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.template.loader import render_to_string


class IndexView(FormView):
    template_name = 'frontpage/index.html'
    form_class = ContactUsForm
    success_url = '/#contact'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['time'] = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M")

        return context

    def form_valid(self, form):
        c = {
            'email': form.cleaned_data['email'],
            'fullname': form.cleaned_data['fullname'],
            'company': form.cleaned_data['company'],
            'message': form.cleaned_data['message'],
            'phone': form.cleaned_data['phone'],
            'site_name': 'AML Global',
        }
        email_template_name = 'frontpage/email/contactus.html'
        subject = "New message from Contact Us form"
        email = render_to_string(email_template_name, c)
        try:
            msg = EmailMessage(
                subject='New message from Contact Us form',
                body=email,
                from_email=settings.EMAIL_FROM_ADDRESS,
                to=[settings.CONTACTUS_MAILTO],
                cc=[settings.CONTACTUS_MAILCC],
            )
            msg.send()
            messages.success(
                self.request, 'Your message has been sent')
        except IOError as e:
            messages.error(
                self.request, f'There was an error when sending your message')
        return redirect('/#contact')
