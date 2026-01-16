resource "aws_apigatewayv2_route" "documents_upload_url" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /documents/upload-url"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}
resource "aws_apigatewayv2_route" "documents_process" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /documents/process"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}
resource "aws_apigatewayv2_route" "translate" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /translate"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}
resource "aws_apigatewayv2_route" "speech_synthezize" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /speech/synthesize"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}
resource "aws_apigatewayv2_route" "transcribe_upload" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /speech/transcribe/upload-url"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}
resource "aws_apigatewayv2_route" "speech_transcribe_process" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /speech/transcribe/process"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_api" "http_api" {
  name          = "${local.name_prefix}-api"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "PUT", "OPTIONS"]
    allow_headers = ["content-type"]
  }
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.sentiment_processor.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "post_message" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /messages"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}
resource "aws_apigatewayv2_route" "speech_transcribe_status" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /speech/transcribe/status"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sentiment_processor.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}
