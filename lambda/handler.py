import json
import os
import uuid
import boto3
from datetime import datetime

# AWS clients
comprehend = boto3.client("comprehend")
sqs = boto3.client("sqs")
s3 = boto3.client("s3")

# Environment variables (AI config)
NEGATIVE_THRESHOLD = float(os.getenv("NEGATIVE_THRESHOLD", "0.7"))
POSITIVE_THRESHOLD = float(os.getenv("POSITIVE_THRESHOLD", "0.7"))
LANGUAGE_CODE = os.getenv("LANGUAGE_CODE", "pt")

# Environment variables (routing)
HIGH_QUEUE_URL = os.environ["HIGH_QUEUE_URL"]
NORMAL_QUEUE_URL = os.environ["NORMAL_QUEUE_URL"]
LOW_QUEUE_URL = os.environ["LOW_QUEUE_URL"]

# Optional audit bucket
AUDIT_BUCKET = os.environ.get("AUDIT_BUCKET")


def lambda_handler(event, context):
    print("EVENT:", json.dumps(event))
    try:
       
        # Parse request body
        body = json.loads(event.get("body", "{}"))
        message = body.get("message")

        if not message or not isinstance(message, str):
            return _response(400, {"error": "Missing or invalid 'message' field"})

        # Sentiment analysis
        sentiment_response = comprehend.detect_sentiment(
            Text=message,
            LanguageCode=LANGUAGE_CODE
        )

        scores = sentiment_response["SentimentScore"]
        sentiment = sentiment_response["Sentiment"]

        # Routing decision
        priority, queue_url = _route(scores)

        payload = {
            "id": str(uuid.uuid4()),
            "message": message,
            "sentiment": sentiment,
            "scores": scores,
            "priority": priority,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Send to SQS
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(payload)
        )

        # Optional audit log to S3
        if AUDIT_BUCKET:
            s3.put_object(
                Bucket=AUDIT_BUCKET,
                Key=f"audit/{payload['id']}.json",
                Body=json.dumps(payload),
                ContentType="application/json"
            )
        friendly_message = build_friendly_message(sentiment, priority)
        return _response(200, { 
            "summary": { 
                "sentiment": sentiment,
                "priority": priority,
                "message": friendly_message
            },
            "data": payload
        })

    except Exception as e:
        # This guarantees the real error shows up in CloudWatch Logs
        print("ERROR:", str(e))
        return _response(500, {"error": "Internal server error"})
def build_friendly_message(sentiment, priority):
    if sentiment == "NEGATIVE":
        return (
            "Thanks for your message. It sounds negative, "
            "so it was marked as high priority for faster attention."
        )

    if sentiment == "POSITIVE":
        return (
            "Thanks for your message! It sounds positive, "
            "so it was routed as low priority."
        )

    return (
        "Thanks for your message. It seems neutral, "
        "so it was routed with normal priority."
    )

def _route(scores):
    if scores.get("Negative", 0) >= NEGATIVE_THRESHOLD:
        return "HIGH", HIGH_QUEUE_URL

    if scores.get("Positive", 0) >= POSITIVE_THRESHOLD:
        return "LOW", LOW_QUEUE_URL

    return "NORMAL", NORMAL_QUEUE_URL


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body)
    }
