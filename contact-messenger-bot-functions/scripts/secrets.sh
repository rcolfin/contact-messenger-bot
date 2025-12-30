#!/usr/bin/env bash

FUSE_SECRETS_VOLUME=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )

EMAIL__HOST="smtp.gmail.com"
EMAIL__PORT=587
EMAIL__AUTH__USER=$(gcloud secrets versions access latest --secret=EMAIL_SERVER_USER)
EMAIL__AUTH__PASSWORD=$(gcloud secrets versions access latest --secret=EMAIL_SERVER_PASSWORD)

export EMAIL__HOST
export EMAIL__PORT
export EMAIL__AUTH__USER
export EMAIL__AUTH__PASSWORD
export FUSE_SECRETS_VOLUME