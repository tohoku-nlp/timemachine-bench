from boto3 import client
from botocore.config import Config

from tenacity import retry, stop_after_delay

from utils.wait_utils import wait_on_retry_after

default_model_id = "us.anthropic.claude-sonnet-4-20250514-v1:0"

default_inference_config = {
    "maxTokens": 512,
    "temperature": 0,
}

# disable default retry strategy from boto3 and apply custom retry instead
default_client_config = Config(
    retries={'max_attempts': 0}
)

bedrock_client = client("bedrock-runtime",
                        region_name="us-east-1",
                        config=default_client_config)

@retry(stop=stop_after_delay(600), wait=wait_on_retry_after())
def get_llm_response(user_input, model_id=default_model_id, inference_config=None):
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "text": user_input
                }
            ]
        }
    ]

    # set temperature to 0, since the installation process is deterministic
    response = bedrock_client.converse(
        modelId=model_id,
        messages=messages,
        inferenceConfig=inference_config or default_inference_config
    )

    return response
