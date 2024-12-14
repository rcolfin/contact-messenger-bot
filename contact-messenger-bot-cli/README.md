# contact-messenger-bot-cli

CLI for interacting with the [contact-messenger-bot-api](../contact-messenger-bot-api/).

For example: Bot to send text messages to Google Contacts for birthday's and anniversaries.

# Development

# Setup Python Environment:

Run [scripts/console.sh](../scripts/console.sh) poetry install

## If you need to relock:

Run [scripts/lock.sh](../scripts/lock.sh)

# Run code

Run [scripts/console.sh](../scripts/console.sh) poetry run python -m contact_messenger_bot.cli list-contacts

# Copy secrets locally

```sh
gcloud storage cp gs://contact-messenger-4ed7624155de0493/* .
```
