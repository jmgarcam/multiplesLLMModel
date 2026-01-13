#!/bin/bash

# Usage example: sudo ./create_network.sh .env.test
# NETWORK_NAME_NEWS is the network name

# Load variables from .env
ENV_FILE=${1:-.env}  # Allows passing a .env file as an argument, default is .env
if [ ! -f "$ENV_FILE" ]; then
  echo "Error: file $ENV_FILE not found"
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

# Verify that NETWORK_NAME_NEWS is defined
if [ -z "$NETWORK_NAME_NEWS" ]; then
  echo "Error: NETWORK_NAME_NEWS is not defined in $ENV_FILE"
  exit 1
fi

# Create the network (if it does not exist)
if docker network ls --format '{{.Name}}' | grep -qw "$NETWORK_NAME_NEWS"; then
  echo "The network '$NETWORK_NAME_NEWS' already exists."
else
  echo "Creating network '$NETWORK_NAME_NEWS'..."
  docker network create "$NETWORK_NAME_NEWS"
  echo "Network '$NETWORK_NAME_NEWS' created."
fi
