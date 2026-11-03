# ESPN Fantasy Football → GroupMe on AWS Lambda

This repository posts an ESPN Fantasy Football matchup report to GroupMe every
hour. It uses AWS Lambda, EventBridge, and one AWS Systems Manager (SSM)
Parameter Store `SecureString` instead of a continuously running server.

## What it costs

The default job invokes Lambda about 744 times per month. AWS Lambda's ongoing
free tier includes 1 million requests and 400,000 GB-seconds per month; this
small 128 MB, 30-second-max function is far below those limits in normal use.
Use a **Standard** Parameter Store parameter: standard parameters and their
standard-throughput API calls have no additional charge. AWS can change pricing
and other account resources can still create charges, so set up a billing alert
before deployment.

## Create the protected SSM parameter

In the AWS Systems Manager console, open **Parameter Store** and create a
parameter with these settings:

- **Name:** `/fantasy-groupme-bot/config` (or another unique name)
- **Tier:** Standard
- **Type:** SecureString
- **KMS key:** `aws/ssm`
- **Value:** one JSON object in this shape:

  ```json
  {
    "ESPN_LEAGUE_ID": "...",
    "ESPN_SEASON": "2026",
    "ESPN_SWID": "{...}",
    "ESPN_S2": "...",
    "GROUPME_BOT_ID": "..."
  }
  ```

Do not use an Advanced parameter or enable higher throughput; either can incur
charges. Do not put this JSON in the repository, a shell command, or a SAM
parameter override.

## AWS deployment

1. Install the [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) and configure the AWS CLI with an AWS account that can create Lambda, IAM, CloudFormation, and EventBridge resources.
2. In the repository, run:

   ```bash
   sam build
   sam deploy --guided
   ```

3. During the guided prompts:

   - Use a unique stack name, such as `fantasy-groupme-bot`.
   - Enter the **SSM parameter name** you created, not the secret values.
   - Allow SAM to create IAM roles.
   - Keep the default `rate(1 hour)` schedule, or enter another valid EventBridge `rate(...)` or `cron(...)` expression.

The first deployment creates the Lambda function and its EventBridge schedule.
The function posts automatically from then on. View run logs in CloudWatch Logs
under `/aws/lambda/<function name>`.

## Cost safety

Create an AWS Budget alert before deploying. Do not add NAT gateways, VPCs,
databases, provisioned concurrency, or Secrets Manager to this small project:
they are unnecessary here and can add charges. The Lambda receives only the SSM
parameter name and has permission to read only that parameter; private values
never enter the repository or Lambda environment configuration.

## Remove the AWS resources

```bash
aws cloudformation delete-stack --stack-name fantasy-groupme-bot
```

Replace the stack name with the one you chose. Verify deletion in the
CloudFormation console before closing the AWS account.
