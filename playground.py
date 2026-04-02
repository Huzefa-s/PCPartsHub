from django.conf import settings

settings.configure(
    PASSWORD_HASHERS=[
        "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    ]
)

from django.contrib.auth.hashers import make_password

print(make_password("hello"))