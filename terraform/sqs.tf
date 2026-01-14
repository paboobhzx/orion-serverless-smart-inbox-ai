
resource "aws_sqs_queue" "low_priority" {
  name = "${local.name_prefix}-low-priority"
  redrive_policy = jsonencode(({
    deadLetterTargetArn = aws_sqs_queue.low_priority_dlq.arn
    maxReceiveCount     = 5
  }))
}
resource "aws_sqs_queue" "low_priority_dlq" {
  name = "${local.name_prefix}-low-priority-dlq"
}



resource "aws_sqs_queue" "normal_priority" {
  name = "${local.name_prefix}-normal-priority"
  redrive_policy = jsonencode(({
    deadLetterTargetArn = aws_sqs_queue.normal_priority_dlq.arn
    maxReceiveCount     = 5
  }))
}
resource "aws_sqs_queue" "normal_priority_dlq" {
  name = "${local.name_prefix}-normal-priority-dlq"
}


resource "aws_sqs_queue" "high_priority" {
  name = "${local.name_prefix}-high-priority"
  redrive_policy = jsonencode(({
    deadLetterTargetArn = aws_sqs_queue.high_priority_dlq.arn
    maxReceiveCount     = 5
  }))
}
resource "aws_sqs_queue" "high_priority_dlq" {
  name = "${local.name_prefix}-high-priority-dlq"
}
