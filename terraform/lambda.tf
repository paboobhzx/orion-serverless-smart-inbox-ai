resource "aws_lambda_function" "sentiment_processor" {
  function_name    = "${local.name_prefix}-sentiment-processor"
  role             = aws_iam_role.lambda_role.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.11"
  timeout          = 10
  filename         = "${path.module}/../lambda/lambda.zip"
  source_code_hash = filebase64sha256(("${path.module}/../lambda/lambda.zip"))
  environment {
    variables = {
      #AI Behavior
      NEGATIVE_THRESHOLD = "0.7"
      POSITIVE_THRESHOLD = "0.7"
      LANGUAGE_CODE      = "pt"
      #Routing
      HIGH_QUEUE_URL   = aws_sqs_queue.high_priority.id
      NORMAL_QUEUE_URL = aws_sqs_queue.normal_priority.id
      LOW_QUEUE_URL    = aws_sqs_queue.low_priority.id
      #Audit
      AUDIT_BUCKET     = aws_s3_bucket.audit_bucket.bucket
      DOCUMENTS_BUCKET = aws_s3_bucket.documents_bucket.bucket
    }
  }

}
