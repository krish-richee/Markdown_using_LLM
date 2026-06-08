#!/bin/bash
mkdir -p data
aws s3 cp s3://retailai-data-bucket/synthetic_retail_data.xlsx data/synthetic_retail_data.xlsx
echo "Data downloaded"
uvicorn main_api:app --host 0.0.0.0 --port $PORT
