#!/usr/bin/env bash

set -euo pipefail

SCRIPT_PATH=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PACKAGE_PATH=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )

cd "${PACKAGE_PATH}" || { >&2 echo "Failed to cd to ${PACKAGE_PATH}."; exit 1; }

if [ ! -f credentials.json ] || [ ! -f token.json ] || [ ! -f zip_code_cache.json ]; then
    echo gcloud storage cp gs://contact-messenger-4ed7624155de0493/*.json .
    gcloud storage cp gs://contact-messenger-4ed7624155de0493/*.json .
fi

BEFORE_CREDENTIALS=$(stat --format '%Z' credentials.json)
BEFORE_TOKEN=$(stat --format '%Z' token.json)
BEFORE_ZIP_CODE_CACHE=$(stat --format '%Z' zip_code_cache.json)

# shellcheck disable=SC1091
source "${SCRIPT_PATH}/secrets.sh"

python -m contact_messenger_bot.api "${@}"

AFTER_CREDENTIALS=$(stat --format '%Z' credentials.json)
AFTER_TOKEN=$(stat --format '%Z' token.json)
AFTER_ZIP_CODE_CACHE=$(stat --format '%Z' zip_code_cache.json)

if [ "${AFTER_CREDENTIALS}" \> "${BEFORE_CREDENTIALS}" ]; then
    echo gcloud storage cp credentials.json gs://contact-messenger-4ed7624155de0493/
    gcloud storage cp credentials.json gs://contact-messenger-4ed7624155de0493/
fi

if [ "${AFTER_TOKEN}" \> "${BEFORE_TOKEN}" ]; then
    echo gcloud storage cp token.json gs://contact-messenger-4ed7624155de0493/
    gcloud storage cp token.json gs://contact-messenger-4ed7624155de0493/
fi

if [ "${AFTER_ZIP_CODE_CACHE}" \> "${BEFORE_ZIP_CODE_CACHE}" ]; then
    echo gcloud storage cp zip_code_cache.json gs://contact-messenger-4ed7624155de0493/
    gcloud storage cp zip_code_cache.json gs://contact-messenger-4ed7624155de0493/
fi

cp ./*.json ../contact-messenger-bot-cli/
cp ./*.json ../contact-messenger-bot-functions/
