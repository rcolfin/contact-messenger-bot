#!/usr/bin/env bash

export EMAIL__HOST="smtp.gmail.com"
export EMAIL__PORT=587
export EMAIL__AUTH__USER=$(gcloud secrets versions access latest --secret=EMAIL_SERVER_USER)
export EMAIL__AUTH__PASSWORD=$(gcloud secrets versions access latest --secret=EMAIL_SERVER_PASSWORD)
