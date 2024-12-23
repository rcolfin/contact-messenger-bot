#!/usr/bin/env bash

set -euo pipefail

SCRIPT_PATH=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PACKAGE_PATH=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )

cd "${PACKAGE_PATH}" || { >&2 echo "Failed to cd to ${PACKAGE_PATH}."; exit 1; }

if [ ! -f credentials.json ] || [ ! -f token.json ] || [ ! -f zip_code_cache.json ] || [ ! -f contacts_svc_cache.pkl ]; then
    echo gcloud storage cp gs://contact-messenger-4ed7624155de0493/* .
    gcloud storage cp gs://contact-messenger-4ed7624155de0493/* .
fi

BEFORE_CREDENTIALS=$(echo 'import os;print(int(os.path.getmtime("credentials.json")))' | python -s)
BEFORE_TOKEN=$(echo 'import os;print(int(os.path.getmtime("token.json")))' | python -s)
BEFORE_ZIP_CODE_CACHE=$(echo 'import os;print(int(os.path.getmtime("zip_code_cache.json")))' | python -s)
BEFORE_CONTACTS_SVC_CACHE=$(echo 'import os;print(int(os.path.getmtime("contacts_svc_cache.pkl")))' | python -s)

# shellcheck disable=SC1091
source "${SCRIPT_PATH}/secrets.sh"

python -m contact_messenger_bot.functions "${@}"

AFTER_CREDENTIALS=$(echo 'import os;print(int(os.path.getmtime("credentials.json")))' | python -s)
AFTER_TOKEN=$(echo 'import os;print(int(os.path.getmtime("token.json")))' | python -s)
AFTER_ZIP_CODE_CACHE=$(echo 'import os;print(int(os.path.getmtime("zip_code_cache.json")))' | python -s)
AFTER_CONTACTS_SVC_CACHE=$(echo 'import os;print(int(os.path.getmtime("contacts_svc_cache.pkl")))' | python -s)

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

if [ "${AFTER_CONTACTS_SVC_CACHE}" \> "${BEFORE_CONTACTS_SVC_CACHE}" ]; then
    echo gcloud storage cp contacts_svc_cache.pkl gs://contact-messenger-4ed7624155de0493/
    gcloud storage cp contacts_svc_cache.pkl gs://contact-messenger-4ed7624155de0493/
fi

cp ./*.json ../contact-messenger-bot-api/
cp ./*.json ../contact-messenger-bot-cli/

cp ./*.pkl ../contact-messenger-bot-api/
cp ./*.pkl ../contact-messenger-bot-cli/
