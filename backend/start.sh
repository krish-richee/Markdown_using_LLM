#!/bin/bash
mkdir -p data
python3 -c "
import boto3, os
s3 = boto3.client('s3',
    region_name=os.getenv('AWS_REGION','us-east-1'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)
s3.download_file('retailai-data-bucket', 'synthetic_retail_data.xlsx', 'data/synthetic_retail_data.xlsx')
print('Excel downloaded from S3')
"
uvicorn main_api:app --host 0.0.0.0 --port $PORT
