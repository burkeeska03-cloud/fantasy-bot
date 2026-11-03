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
charges. Do not put this JSON in the repository, a shell command, or Terraform
variables.

## Terraform deployment

1. Install [Terraform](https://developer.hashicorp.com/terraform/install) and configure the AWS CLI with an AWS account that can create Lambda, IAM, CloudWatch, and EventBridge resources.
2. In the repository, initialize and preview the Terraform configuration:

   ```bash
   terraform init
   terraform plan -var='ssm_parameter_name=/fantasy-groupme-bot/config'
   ```

3. Apply the reviewed plan:

   ```bash
   terraform apply -var='ssm_parameter_name=/fantasy-groupme-bot/config'
   ```

Terraform creates the Lambda function, least-privilege IAM role, seven-day log
retention, and EventBridge schedule. The function posts automatically from then
on. View run logs in CloudWatch Logs under `/aws/lambda/fantasy-groupme-bot`.

To change the schedule, add a second variable when planning and applying—for
example, `-var='schedule_expression=rate(2 hours)'`.

## Cost safety

Create an AWS Budget alert before deploying. Do not add NAT gateways, VPCs,
databases, provisioned concurrency, or Secrets Manager to this small project:
they are unnecessary here and can add charges. The Lambda receives only the SSM
parameter name and has permission to read only that parameter; private values
never enter the repository or Lambda environment configuration.

## Remove the AWS resources

```bash
terraform destroy -var='ssm_parameter_name=/fantasy-groupme-bot/config'
```

Use the same parameter name and Region used for deployment. This does not delete
the manually created SSM parameter, so delete it separately if it is no longer
needed.
