# contact-messenger-bot-cli

CLI for interacting with the [contact-messenger-bot-api](../contact-messenger-bot-api/).

For example: Bot to send text messages to Google Contacts for birthday's and anniversaries.

```sh
python -m contact_messenger_bot.cli list-contacts
```

To copy the secrets locally:

```sh
gcloud storage cp gcs://contact-messenger-4ed7624155de0493/* .
```
