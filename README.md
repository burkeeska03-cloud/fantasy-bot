# ESPN Fantasy Football → GroupMe on AWS Lambda

This repository posts an ESPN Fantasy Football matchup report to GroupMe every
hour. It uses AWS Lambda and EventBridge instead of a continuously running
server, so an hourly schedule is comfortably within the AWS Lambda free tier.

## What it costs

The default job invokes Lambda about 744 times per month. AWS Lambda's ongoing
free tier includes 1 million requests and 400,000 GB-seconds per month; this
small 128 MB, 30-second-max function is far below those limits in normal use.
AWS can change pricing and other account resources can still create charges, so
set up a billing alert before deployment.

## Local check

```bash
cp .env.example .env
open -e .env
python3 fantasy_bot.py
```

Use `python3 fantasy_bot.py --post` only when you want to send a manual test.

## AWS deployment

1. Install the [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) and configure the AWS CLI with an AWS account that can create Lambda, IAM, CloudFormation, and EventBridge resources.
2. In the repository, run:

   ```bash
   sam build
   sam deploy --guided
   ```

3. During the guided prompts:

   - Use a unique stack name, such as `fantasy-groupme-bot`.
   - Enter your ESPN and GroupMe values as parameter overrides. Do not commit them.
   - Allow SAM to create IAM roles.
   - Keep the default `rate(1 hour)` schedule, or enter another valid EventBridge `rate(...)` or `cron(...)` expression.

The first deployment creates the Lambda function and its EventBridge schedule.
The function posts automatically from then on. View run logs in CloudWatch Logs
under `/aws/lambda/<function name>`.

## Cost safety

Create an AWS Budget alert before deploying. Do not add NAT gateways, VPCs,
databases, provisioned concurrency, or Secrets Manager to this small project:
they are unnecessary here and can add charges. Lambda environment variables hold
the private values; they are excluded from this repository.

## Remove the AWS resources

```bash
aws cloudformation delete-stack --stack-name fantasy-groupme-bot
```

Replace the stack name with the one you chose. Verify deletion in the
CloudFormation console before closing the AWS account.
