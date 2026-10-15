from .development import *

DEBUG = False

# Tests never need a broker: tasks run inline.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = False

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# No log files from the test suite.
LOGGING = {'version': 1, 'disable_existing_loggers': False}
