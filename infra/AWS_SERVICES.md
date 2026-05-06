# AWS services used by weather-etl

A guided reference for navigating the AWS console and finding the resources
this project created. Everything lives in **`us-west-2` (Oregon)** — make sure
that's selected in the region picker (top-right of the console) before
exploring, otherwise the resources will appear "missing".

Account: **351578878554**.

---

## Service-by-service map

| # | Service | What the service does (in general) | What we use it for | Resource name | Where in the console |
|---|---|---|---|---|---|
| 1 | **ECR** (Elastic Container Registry) | Stores Docker images, like a private Docker Hub | Holds the `weather-etl` image our pipeline runs from | Repository: `weather-etl` (URI: `351578878554.dkr.ecr.us-west-2.amazonaws.com/weather-etl`) | ECR → Repositories → weather-etl → Images |
| 2 | **Secrets Manager** | Encrypted storage for credentials, keys, etc. | Holds Snowflake `account`, `user`, `private_key` as one JSON secret | Secret: `weather-etl/snowflake` | Secrets Manager → Secrets → weather-etl/snowflake |
| 3 | **IAM** (Identity & Access Management) | Defines who/what can do what | Two roles: one for the ECS task to use, one for EventBridge Scheduler | `weather-etl-task-execution-role`, `weather-etl-scheduler-role` | IAM → Roles (filter on "weather-etl") |
| 4 | **ECS** (Elastic Container Service) | Runs Docker containers as managed tasks | Defines and launches the pipeline as a Fargate task | Cluster: `weather-etl`; Task definition: `weather-etl:N` | ECS → Clusters → weather-etl, and ECS → Task Definitions |
| 5 | **Fargate** | Serverless compute *within* ECS — no servers to manage | The "engine" our ECS task runs on (CPU, memory, ARM64 Graviton arch) | (no separate UI — appears as the launch type inside ECS) | (visible on the cluster's Tasks tab and on the task definition's "Compatibility" line) |
| 6 | **CloudWatch Logs** | Centralized log storage and search | Captures everything the container prints to stdout/stderr | Log group: `/ecs/weather-etl` (one log stream per task run) | CloudWatch → Log groups → /ecs/weather-etl |
| 7 | **EventBridge Scheduler** | A cron service for AWS — fires actions on a schedule | Runs the ECS task daily at 13:00 UTC | Schedule: `weather-etl-daily` | Amazon EventBridge → Scheduler → Schedules |
| 8 | **VPC** (Virtual Private Cloud) | Networking — subnets, security groups, IPs | We use the **default** VPC + a public subnet + the default security group so the task can reach Open-Meteo + Snowflake + AWS service endpoints | VPC: `vpc-021508ed1c3ffd1ff`, Subnet: `subnet-032b35e03736a3004`, SG: `sg-00788a212f801b9b1` | VPC → Your VPCs (look for the one marked "default") |

---

## Suggested tour order (10–15 min)

This walks left-to-right through the data flow: image → secret → role → run → logs → schedule.

1. **ECR — start here.** See the image you pushed.
   - ECR → Repositories → `weather-etl` → Images.
   - You'll see the `v1`, `v2`, and `latest` tags pointing at the same digest. The image is ~194 MB compressed.

2. **Secrets Manager — what Fargate fetches at runtime.**
   - Secrets Manager → Secrets → `weather-etl/snowflake`.
   - Click "Retrieve secret value" → "Plaintext" to see the JSON shape: `{"account":"...","user":"...","private_key":"-----BEGIN PRIVATE KEY-----..."}`. **Don't share this view with anyone.**
   - Note the ARN at the top — that's what the task definition references.

3. **IAM — the two roles.**
   - IAM → Roles → search for `weather-etl`.
   - Click `weather-etl-task-execution-role`. On the **Permissions** tab you'll see:
     - **Managed policy** `AmazonECSTaskExecutionRolePolicy` — lets the task pull from ECR and write to CloudWatch.
     - **Inline policy** `read-snowflake-secret` — narrowly grants `secretsmanager:GetSecretValue` on just our specific secret ARN.
   - On the **Trust relationships** tab: only `ecs-tasks.amazonaws.com` is allowed to assume this role.
   - Then click `weather-etl-scheduler-role`. Inline policy permits `ecs:RunTask` on the task definition family + `iam:PassRole` for the execution role above. Trust policy: `scheduler.amazonaws.com`.

4. **ECS Cluster — where tasks actually run.**
   - ECS → Clusters → `weather-etl`.
   - **Tasks** tab: shows running and recently-stopped tasks. Click any stopped task to see exit code, stop reason, started/stopped timestamps, and a link straight to its log stream.
   - **Tasks** tab → "Stopped" filter: see history of every run (including the manual one we did + tomorrow's scheduled one once it fires).
   - Top of the cluster page: a **"Run new task"** button — useful if you ever want to fire one off from the UI instead of the CLI.

5. **ECS Task Definition — the recipe.**
   - ECS → Task definitions → `weather-etl` → revision 1.
   - **JSON** tab — exactly the contents of `infra/task-definition.json` in this repo.
   - **Container definitions** tab — shows the env vars (visible) and the secrets (references only — values stay in Secrets Manager).
   - Notice **CPU architecture: ARM64** (because we're running on Graviton).

6. **CloudWatch Logs — actual run output.**
   - CloudWatch → Log groups → `/ecs/weather-etl`.
   - You'll see one log stream per task run, named like `ecs/app/<task-id>`.
   - Click the most recent stream — you can see the full ETL + dbt build output.
   - Try the **"Live tail"** button on the log group page — useful when you fire a manual run.

7. **EventBridge Scheduler — the cron.**
   - EventBridge → Schedules → `weather-etl-daily`.
   - **Schedule pattern**: cron(0 13 * * ? *) UTC = 13:00 UTC daily.
   - **Target**: Amazon ECS RunTask → cluster `weather-etl`, task definition `weather-etl`, with the network config we set.
   - **Permissions**: shows it uses `weather-etl-scheduler-role`.
   - You can **disable** the schedule from this page if you ever want to pause it (no resources are billed while disabled).

8. **(Optional) VPC — networking.**
   - VPC → Your VPCs → the one with **Default VPC = Yes**.
   - Subnets → see the public subnets (one per Availability Zone). Our task uses `subnet-032b35e03736a3004`.
   - Security Groups → `default` SG. By default it allows all outbound traffic, which is what the task needs (egress to Open-Meteo, Snowflake, AWS service endpoints).

---

## What the runtime data flow looks like

When the schedule fires (or you run a task manually), here's the order of operations across these services:

```
EventBridge Scheduler
    └─ assumes weather-etl-scheduler-role
        └─ calls ecs:RunTask on cluster=weather-etl, taskDefinition=weather-etl:N

ECS / Fargate
    ├─ assumes weather-etl-task-execution-role
    ├─ pulls image from ECR (uses execution role's ECR perms)
    ├─ fetches secret from Secrets Manager (uses inline read-snowflake-secret policy)
    ├─ injects secret JSON fields as env vars: SNOWFLAKE_ACCOUNT / USER / PRIVATE_KEY
    ├─ launches the container in default VPC's public subnet
    └─ streams stdout/stderr to /ecs/weather-etl in CloudWatch

Inside the container
    ├─ entrypoint.sh writes SNOWFLAKE_PRIVATE_KEY env var to /tmp/snowflake_private_key.pem
    ├─ python etl.py    ── HTTPS to api.open-meteo.com → load to Snowflake
    └─ dbt build        ── connects to Snowflake → builds models + runs tests
```

---

## Costs at a glance

Roughly **$0.50/month** at this volume:

| Service | Driver | Approx cost |
|---|---|---|
| Fargate (Graviton) | ~85 sec × 30 days × 0.25 vCPU + 0.5 GB | < $0.05/mo |
| Secrets Manager | $0.40 per secret per month | $0.40/mo |
| ECR storage | 194 MB × $0.10/GB-mo | $0.02/mo |
| CloudWatch Logs | Tiny ingest at this volume | < $0.01/mo |
| EventBridge Scheduler | Free up to 14M invocations/mo | $0 |
| VPC / data transfer | Default VPC, no NAT gateway | $0 |

Add a CloudWatch billing alarm if you want a safety net — Billing → Budgets is the standard place.

---

## Quick tip: use the CLI to find anything in the UI

If you ever lose track of where something is, the CLI command for any resource includes the URL pattern. Examples:

```bash
# Show all our schedules
aws scheduler list-schedules --region us-west-2

# Show all task definitions in the family
aws ecs list-task-definitions --family-prefix weather-etl --region us-west-2

# Tail the most recent log stream
LATEST=$(aws logs describe-log-streams --log-group-name /ecs/weather-etl \
    --order-by LastEventTime --descending --max-items 1 \
    --region us-west-2 --query 'logStreams[0].logStreamName' --output text)
aws logs tail /ecs/weather-etl --log-stream-names "$LATEST" --region us-west-2
```
