import json
import os
import uuid
import boto3
from datetime import datetime

# AWS clients
comprehend = boto3.client("comprehend")
sqs = boto3.client("sqs")
s3 = boto3.client("s3")
translate = boto3.client("translate")

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
DOCUMENTS_BUCKET = os.environ["DOCUMENTS_BUCKET"]


def lambda_handler(event, context):
    print("EVENT:", json.dumps(event))

    path = event.get("rawPath", "")
    body = json.loads(event.get("body", "{}"))

    if path == "/translate":
        return handle_translate(body)

    if path == "/messages":
        return handle_messages(body)
    
    if path == "/documents/upload-url": 
        return handle_document_upload_url(body)
    
    if path == "/documents/process": 
        return handle_document_process(body)
    if path == "/speech/transcribe/upload-url": 
        return handle_audio_upload_url(body)
    
    if path == "/speech/transcribe/process":
        return handle_audio_transcribe(body)
    
    if path == "/speech/synthesize":
        return handle_text_to_speech(body)
    
    if path == "speech/transcribe/status":
        return handle_transcribe_status(event.get("queryStringParameters, {}"))

    return _response(404, {"error": "Route not found"})

#Document Processing
def handle_document_process(body):
    bucket = body.get("bucket")
    key = body.get("key")

    if not bucket or not key:
        return _response(400, {"error": "bucket and key are required"})
    textract = boto3.client("textract")
    #Run OCR
    textract_response = textract.detect_document_text(
        Document={ 
            "S3Object": { 
                "Bucket": bucket,
                "Name": key
            }
            
        }
    )
    lines = [ 
        block["Text"]
        for block in textract_response.get("Blocks", [])
        if block["BlockType"] == "LINE"
    ]
    extracted_text = " ".join(lines)

    if not extracted_text.strip():
        return _response(400, {"error": "No text detected in the document"})
    
    #Sentiment analysis (reusing the same logic)
    sentiment_response = comprehend.detect_sentiment(
        Text=extracted_text[:4500],
        LanguageCode=LANGUAGE_CODE
    )
    scores = sentiment_response["SentimentScore"]
    sentiment = sentiment_response["Sentiment"]
    priority, queue_url = _route(scores)
    payload = { 
        "id": str(uuid.uuid4()),
        "source": "document",
        "s3:bucket": bucket,
        "s3_key": key,
        "extracted_text": extracted_text,
        "sentiment": sentiment,
        "scores": scores,
        "priority": priority,
        "timestamp": datetime.utcnow().isoformat()
    }
    #Send to SQS
    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(payload)

    )
    # Audit Log
    if AUDIT_BUCKET:
        s3.put_object(
            Bucket=AUDIT_BUCKET,
            Key=f"audit/documents/{payload['id']}.json",
            Body=json.dumps(payload),
            ContentType="application/json"
        )
    return _response(200,{ 
        "sentiment": sentiment,
        "priority": priority,
        "extracted_text_preview": extracted_text[:500]
    })
# -----------------------
# Sentiment handling
# -----------------------

def handle_messages(body):
    message = body.get("message")

    if not message or not isinstance(message, str):
        return _response(400, {"error": "Missing or invalid 'message' field"})

    sentiment_response = comprehend.detect_sentiment(
        Text=message,
        LanguageCode=LANGUAGE_CODE
    )

    scores = sentiment_response["SentimentScore"]
    sentiment = sentiment_response["Sentiment"]

    priority, queue_url = _route(scores)

    payload = {
        "id": str(uuid.uuid4()),
        "message": message,
        "sentiment": sentiment,
        "scores": scores,
        "priority": priority,
        "timestamp": datetime.utcnow().isoformat()
    }

    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(payload)
    )

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


# -----------------------
# Translation handling
# -----------------------

def handle_translate(body):
    text = body.get("text")
    source_lang = body.get("source_language", "auto")
    target_lang = body.get("target_language")

    if not text or not target_lang:
        return _response(400, {"error": "Missing text or target_language"})

    result = translate.translate_text(
        Text=text,
        SourceLanguageCode=source_lang,
        TargetLanguageCode=target_lang
    )

    return _response(200, {
        "original_text": text,
        "translated_text": result["TranslatedText"],
        "detected_language": result.get("SourceLanguageCode"),
        "target_language": target_lang
    })


# -----------------------
# Helpers
# -----------------------

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
#Document upload handling
def handle_document_upload_url(body):
    file_name = body.get("file_name")
    content_type = body.get("content_type")
    if not file_name or not content_type:
        return _response(400, {"error": "file_name and content_type are required"})
    bucket = DOCUMENTS_BUCKET
    key = f"uploads/documents/{uuid.uuid4()}-{file_name}"
    s3_client = boto3.client("s3")

    upload_url = s3_client.generate_presigned_url(
        ClientMethod="put_object",
        Params={ 
            "Bucket": bucket,
            "Key": key,
            "ContentType": content_type
        },
        ExpiresIn=300 #5 minutes
    )
    return _response(200, { 
        "upload_url": upload_url,
        "bucket": bucket,
        "key": key
    })
def handle_audio_upload_url(body):
    file_name = body.get("file_name")
    content_type = body.get("content_type", "audio/mpeg")
    if not file_name:
        return _response(400, { "error": "file_name is required"})
    key = f"uploads/audio/{uuid.uuid4()}-{file_name}"

    url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={ 
            "Bucket": DOCUMENTS_BUCKET,
            "Key": key,
            "ContentType": content_type
        },
        ExpiresIn=900
    )

    return _response(200, { 
        "upload_url": url,
        "bucket": DOCUMENTS_BUCKET,
        "key": key
    })

def handle_audio_transcribe(body):
    bucket = body.get("bucket")
    key = body.get("key")
    language = body.get("language", "pt-BR")

    if not bucket or not key:
        return _response(400, { "error": "bucket and key are required"})
    
    job_name = f"transcribe-{uuid.uuid4()}"
    transcribe = boto3.client("transcribe")
    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={ 
            "MediaFileUri": f"s3://{bucket}/{key}"
        },
        MediaFormat=key.split(".")[-1],
        LanguageCode=language,
        OutputBucketName=bucket,
        OutputKey=f"outputs/transcriptions/{job_name}.json"
    )
    return _response(200, { 
        "job_name": job_name,
        "status": "IN_PROGRESS"
    })

def handle_text_to_speech(body):
    text = body.get("text")
    voice = body.get("voice", "Camila")
    language = body.get("language","pt-BR")

    if not text:
        return _response(400, { "error": "text is required"})
    
    polly = boto3.client("polly")
    response = polly.synthesize_speech(
        Text=text,
        OutputFormat="mp3",
        VoiceId=voice,
        LanguageCode=language
    )

    audio_key = f"outputs/speech/{uuid.uuid4()}.mp3"

    s3.put_object(
        Bucket=DOCUMENTS_BUCKET,
        Key=audio_key,
        Body=response["AudioStream"].read(),
        ContentType="audio/mpeg"
    )
    audio_url = s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={ 
            "Bucket": DOCUMENTS_BUCKET,
            "Key": audio_key
        },
        ExpiresIn=900
    )

    return _response(200, { 
        "audio_url": audio_url
    })

def handle_transcribe_status(query):
    job_name = query.get("job_name")

    if not job_name:
        return _response(400, { "error": "job_name is required"})
    
    transcribe = boto3.client("transcribe")
    job = transcribe.get_transcription_job(
        TranscriptionJobName=job_name 
    )

    status = job["TranscriptionJob"]["TranscriptionJobStatus"]

    response = { 
        "job_name": job_name,
        "status": status
    }

    if status == "COMPLETED":
        response["transcript_uri"] = job["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]

    return _response(200, response)