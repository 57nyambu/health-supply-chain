import copy
import io
import os

import boto3
import pytest
from moto import mock_aws

BUCKET = "afyasync-test"


@pytest.fixture
def local_store(settings, tmp_path):
    """Point the local backend at a temporary directory (never the real data/)."""
    stores = copy.deepcopy(settings.STORAGES)
    stores["local"]["OPTIONS"]["location"] = tmp_path / "objects"
    settings.STORAGES = stores
    settings.STORAGE_BACKEND = "local"
    return tmp_path / "objects"


@pytest.fixture
def s3_store(settings, local_store):
    """An in-memory S3 bucket (moto); MinIO covers the same path in compose/CI."""
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
        stores = copy.deepcopy(settings.STORAGES)
        stores["s3"]["OPTIONS"].update(
            bucket_name=BUCKET,
            region_name="us-east-1",
            endpoint_url=None,
            access_key="synthetic-test-key",
            secret_key="synthetic-test-secret",
        )
        settings.STORAGES = stores
        settings.RESIDENCY_ALLOWED_HOSTS = ["s3.amazonaws.com"]
        settings.STORAGE_BACKEND = "s3"
        yield boto3.client("s3", region_name="us-east-1")


@pytest.fixture(params=["local", "s3"])
def backend(request):
    """Run a test once per storage backend."""
    request.getfixturevalue("local_store" if request.param == "local" else "s3_store")
    return request.param


def pdf_bytes(size: int = 64) -> bytes:
    return b"%PDF-1.4\n" + os.urandom(size)


def upload_file(data: bytes, name: str = "scan.pdf") -> io.BytesIO:
    handle = io.BytesIO(data)
    handle.name = name
    return handle


@pytest.fixture
def s3_http_store(settings, local_store):
    """A real HTTP S3 endpoint (moto server) reached through S3_ENDPOINT_URL, path-style and
    SigV4 — the same client path MinIO or a Kenyan provider would see."""
    from moto.server import ThreadedMotoServer

    server = ThreadedMotoServer(ip_address="127.0.0.1", port=0, verbose=False)
    server.start()
    host, port = server.get_host_and_port()
    endpoint = f"http://{host}:{port}"
    try:
        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name="us-east-1",
            aws_access_key_id="synthetic-test-key",
            aws_secret_access_key="synthetic-test-secret",
        )
        client.create_bucket(Bucket=BUCKET)
        stores = copy.deepcopy(settings.STORAGES)
        stores["s3"]["OPTIONS"].update(
            bucket_name=BUCKET,
            region_name="us-east-1",
            endpoint_url=endpoint,
            access_key="synthetic-test-key",
            secret_key="synthetic-test-secret",
        )
        settings.STORAGES = stores
        settings.S3_ENDPOINT_URL = endpoint
        settings.RESIDENCY_ALLOWED_HOSTS = [host]
        settings.STORAGE_BACKEND = "s3"
        yield client
    finally:
        server.stop()
