# Security Policy

## Sensitive data

Never include API keys, `.env` files, delivery-note photos, customer contact details, generated audit logs or real order exports in issues or commits.

API keys are read from `OPENAI_API_KEY`, a local `.env`, or Windows Credential Manager. Logs redact strings shaped like OpenAI secret keys.

## Reporting a vulnerability

Do not open a public issue containing credentials or customer data. Use GitHub's
private security advisory feature (Security → Report a vulnerability), or
contact the repository owner privately.

Revoke any exposed key immediately from the OpenAI API key page and replace it with a new key.

