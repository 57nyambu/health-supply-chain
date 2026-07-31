from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

class EmailService:
    @staticmethod
    def send_email(subject, recipient, template_name, context):
        html_content = render_to_string(f"integrations/emails/{template_name}", context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient]
        )
        email.attach_alternative(html_content, "text/html")
        
        try:
            email.send()
            return True
        except Exception as e:
            return False

    def send_welcome_email(self, user, temp_password):
        context = {
            'user': user,
            'temp_password': temp_password,
            'site_name': getattr(settings, 'SITE_NAME', 'Our System')
        }
        return self.send_email(
            subject=f"Your {context['site_name']} Work Credentials",
            recipient=user.email,
            template_name="welcome_credentials.html",
            context=context
        )
    
    def send_password_reset(self, user, reset_link):
        context = {
            'user': user,
            'reset_link': reset_link,
            'site_url': settings.SITE_URL
        }
        return self.send_email(
            subject="Password Reset Request",
            recipient=user.email,
            template_name="password_reset.html",
            context=context
        )