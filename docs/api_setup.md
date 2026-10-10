# API setup

Create a local `.env` file from the example file before running workflows that require credentials.

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

## Important rules

- Never commit `.env` to source control.
- Keep real values only in your local machine environment.
- Use placeholders in `.env.example` only.
- Do not print secret values in logs or UI.
- Only call APIs from Python code, never from frontend JavaScript.
