resource "aws_s3_bucket" "audit_bucket" {
  bucket = "${local.name_prefix}-audit"
}
resource "aws_s3_bucket_versioning" "audit_versioning" {
  bucket = aws_s3_bucket.audit_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}
