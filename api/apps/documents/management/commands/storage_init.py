from typing import Any

from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.documents import storage


class Command(BaseCommand):
    help = (
        "Prepare storage: create DATA_DIR/objects and, when S3 is configured, the bucket "
        "(development and CI; production buckets are created and locked down by operations)."
    )

    def handle(self, *args: Any, **options: Any) -> None:
        local = storage.get_backend("local")
        location = getattr(local, "location", "")
        if location:
            from pathlib import Path

            Path(location).mkdir(parents=True, exist_ok=True)
            self.stdout.write(f"local: {location}")
        if not settings.S3_BUCKET:
            return
        if settings.DJANGO_ENV == "prod":
            raise CommandError("storage_init does not create buckets in production.")
        s3: Any = storage.get_backend("s3")
        client = s3.connection.meta.client
        try:
            client.head_bucket(Bucket=settings.S3_BUCKET)
            self.stdout.write(f"s3: bucket {settings.S3_BUCKET} exists")
        except ClientError:
            client.create_bucket(Bucket=settings.S3_BUCKET)
            self.stdout.write(self.style.SUCCESS(f"s3: created bucket {settings.S3_BUCKET}"))
