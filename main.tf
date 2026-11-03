terraform {
  required_version = ">= 1.6.0"

  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

data "archive_file" "fantasy_bot" {
  type        = "zip"
  source_file = "${path.module}/fantasy_bot.py"
  output_path = "${path.module}/fantasy_bot.zip"
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "read_bot_config" {
  statement {
    effect    = "Allow"
    actions   = ["ssm:GetParameter"]
    resources = [local.ssm_parameter_arn]
  }
}

locals {
  function_name     = "fantasy-groupme-bot"
  ssm_parameter_arn = "arn:${data.aws_partition.current.partition}:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.ssm_parameter_name}"
}

resource "aws_iam_role" "lambda" {
  name               = "${local.function_name}-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "read_bot_config" {
  name   = "read-fantasy-bot-configuration"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.read_bot_config.json
}

resource "aws_cloudwatch_log_group" "fantasy_bot" {
  name              = "/aws/lambda/${local.function_name}"
  retention_in_days = 7
}

resource "aws_lambda_function" "fantasy_bot" {
  function_name    = local.function_name
  description      = "Posts current ESPN Fantasy Football matchups to GroupMe."
  filename         = data.archive_file.fantasy_bot.output_path
  source_code_hash = data.archive_file.fantasy_bot.output_base64sha256
  handler          = "fantasy_bot.lambda_handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda.arn
  architectures    = ["x86_64"]
  memory_size      = 128
  timeout          = 30

  environment {
    variables = {
      SSM_PARAMETER_NAME = var.ssm_parameter_name
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.fantasy_bot,
    aws_iam_role_policy_attachment.lambda_logs,
    aws_iam_role_policy.read_bot_config,
  ]
}

resource "aws_cloudwatch_event_rule" "hourly_update" {
  name                = "${local.function_name}-hourly"
  description         = "Posts the current ESPN fantasy matchup report to GroupMe."
  schedule_expression = var.schedule_expression
}

resource "aws_cloudwatch_event_target" "fantasy_bot" {
  rule = aws_cloudwatch_event_rule.hourly_update.name
  arn  = aws_lambda_function.fantasy_bot.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fantasy_bot.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.hourly_update.arn
}
