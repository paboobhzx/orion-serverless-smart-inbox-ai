output "queues" {
  value = {
    high   = aws_sqs_queue.high_priority.name
    normal = aws_sqs_queue.normal_priority.name
    low    = aws_sqs_queue.low_priority.name
  }
}
output "api_url" {
  value = aws_apigatewayv2_api.http_api.api_endpoint
}
