variable "aws_region" {
  type        = string
  description = "AWS Region for the Lambda, EventBridge rule, and SSM parameter."
  default     = "us-east-1"
}

variable "ssm_parameter_name" {
  type        = string
  description = "Existing Standard SecureString parameter containing the bot configuration JSON."

  validation {
    condition     = startswith(var.ssm_parameter_name, "/")
    error_message = "The SSM parameter name must start with a slash, for example /fantasy-groupme-bot/config."
  }
}

variable "schedule_expression" {
  type        = string
  description = "EventBridge schedule expression."
  default     = "rate(1 hour)"
}
