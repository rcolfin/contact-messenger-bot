# contact-messenger-bot-functions

Ths package represents the Google Cloud Run functions that interact with the [contact-messenger-bot-api](../contact-messenger-bot-api/).

## Development

### Setup Python Environment:

Run [scripts/console.sh](../scripts/console.sh)

### If you need to relock:

Run [scripts/lock.sh](../scripts/lock.sh)

### Run code

Run [scripts/console.sh](../scripts/console.sh) uv run python -m contact_messenger_bot.functions dev

# Create a Proxy to the Deployed Instance

```sh
gcloud run services proxy contact-messenger-bot --port=8080 --region=us-central1
```

# Test locally

1. Start the dev server:

```sh
./scripts/launch.sh dev --target send_messages
```

2. Then open a browser to http://127.0.0.1:8080?date=2024-11-10&groups=family&dry-run=true
