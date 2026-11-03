output "lambda_function_name" {
  description = "Name of the deployed Lambda function."
  value       = aws_lambda_function.fantasy_bot.function_name
}

output "eventbridge_rule_name" {
  description = "Name of the EventBridge schedule rule."
  value       = aws_cloudwatch_event_rule.hourly_update.name
}
