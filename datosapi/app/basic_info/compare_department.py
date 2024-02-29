import json
import httpx
import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
import boto3
import os
from botocore.exceptions import ClientError
import logging

from ...core.config import config

security = config(section="security")

class Constants:
    REGION_NAME = "us-east-1"
    aws_access_key_id = os.getenv('aws_access_key_id')
    aws_secret_access_key = os.getenv('aws_secret_access_key')
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
    S3_BUCKET_NAME_HIERARCHY = os.getenv('S3_BUCKET_NAME_HIERARCHY')


def get_department(url: str, params: dict = None):
    response = httpx.get(url, params=params)
    response.raise_for_status()
    return response.json()

def upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_name)

    # Upload the file
    s3_client = boto3.client(
        "s3",
        region_name=Constants.REGION_NAME,
        aws_access_key_id=Constants.aws_access_key_id,
        aws_secret_access_key=Constants.aws_secret_access_key,
    )
    try:
        s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True

def compare_files(department_file: str = f"{ROOT}/basic_info/department.json"):

    return upload_file(department_file, f'{Constants.S3_BUCKET_NAME}', f"{Constants.S3_BUCKET_NAME_HIERARCHY}/department.json")


if __name__ == "__main__":
    compare_files()