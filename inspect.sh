#!/bin/bash

CLUSTER_NAME="api-test-Cluster-jGAd1ckpBU8v"
TASK_ID="e600c107f6394e8b94b03e4634491f6d"

# Get the container name
CONTAINER_NAME=$(aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks $TASK_ID --query "tasks[0].containers[0].name" --output text)

# Run the command
aws ecs execute-command --cluster $CLUSTER_NAME --task $TASK_ID --container $CONTAINER_NAME --command "df -h" --interactive
