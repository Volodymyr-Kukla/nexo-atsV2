from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create demo users for development (HR, Recruiter, Viewer)"

    def handle(self, *args, **options):
        User = get_user_model()

        demo = [
            ("hr@example.com", "Hr12345678!", "HR_MANAGER", "HR Manager"),
            ("recruiter@example.com", "Recruiter12345678!", "RECRUITER", "Recruiter"),
            ("viewer@example.com", "Viewer12345678!", "VIEWER", "Viewer"),
        ]

        for email, password, role, position in demo:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "role": role,
                    "position": position,
                    "is_active": True,
                },
            )

            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created {email} ({role})"))
            else:
                self.stdout.write(f"Exists: {email} ({user.role})")
