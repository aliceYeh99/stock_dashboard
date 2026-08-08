# common/Config.py
import json

import boto3, os
client = boto3.client("lambda")

s3 = boto3.client("s3")

class Config:

    def __init__(self, bucket_name, key="config/config.json"):
        self.s3 = boto3.client("s3")

        # 本機開發
        if not os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
            with open("/dev/backtest/config/config.json", "r", encoding="utf-8") as f:
                self.data = json.load(f)
            return

        # Lambda

        obj = self.s3.get_object(
            Bucket=bucket_name,
            Key=key
        )

        self.data = json.loads(
            obj["Body"].read()
        )

    def get(self, key, default=None):
        return self.data.get(key, default)

    @property
    def bot_token(self):
        return self.data["BOT_TOKEN"]

    @property
    def chat_id(self):
        return self.data["CHAT_ID"]

    @property
    def topic_arn(self):
        return self.data["TOPIC_ARN"]