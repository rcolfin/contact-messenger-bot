# contact-messenger-bot-functions

Ths package represents the Google Cloud Run functions that interact with the [contact-messenger-bot-api](../contact-messenger-bot-api/).

# Development

# Setup Python Environment:

Run [scripts/console.sh](../scripts/console.sh) poetry install

## If you need to relock:

Run [scripts/lock.sh](../scripts/lock.sh)

# Run code

Run [scripts/console.sh](../scripts/console.sh) poetry run python -m contact_messenger_bot.functions dev

# Create a Proxy to the Deployed Instance

```sh
gcloud run services proxy contact-messenger-bot --port=8080 --region=us-central1
```
