
resource "aws_iam_policy" "lambda_policy" {
  name = "${local.name_prefix}-lambda-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      #CloudWatch Logs
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"

        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      #Amazon Comprehend
      {
        Effect = "Allow"
        Action = [
          "comprehend:DetectSentiment"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.audit_bucket.arn}/*"
      },
      #Amazon SQS (Send only)
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = [
          aws_sqs_queue.high_priority.arn,
          aws_sqs_queue.normal_priority.arn,
          aws_sqs_queue.low_priority.arn
        ]
      },
      #Amazon Translate
      {
        Effect = "Allow"
        Action = [
          "translate:TranslateText",
          "comprehend:DetectDominantLanguage"
        ]
        Resource = "*"
      },
      #Amazon Textract
      {
        Effect = "Allow"
        Action = [
          "textract:DetectDocumentText"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.documents_bucket.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "textract:DetectDocumentText"
        ]
        Resource = "*"
      }
    ]
  })
}
resource "aws_iam_role" "lambda_role" {
  name = "${local.name_prefix}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}
resource "aws_iam_role_policy_attachment" "lambda_policy_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}
