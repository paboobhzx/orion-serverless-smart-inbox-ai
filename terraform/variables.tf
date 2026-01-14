variable "aws_region"{ 
    description = "AWS Region"
    type = string
    default = "us-east-1"
}
variable "project_name"{ 
    description = "Project name prefix"
    type = string 
    default = "serverless-smart-inbox-ai"
}
variable "environment"{ 
    description = "Environment name"
    type = string
    default = "dev"
}