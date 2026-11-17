# Product Discovery Copilot — Desktop MVP

A Windows-oriented desktop prototype that supports **manual product discovery** and an optional **meeting-to-discovery** workflow. Built with Python, Tkinter, the OpenAI Python SDK, and local JSON storage.

> **Portfolio status:** V3.3 source snapshot from September 2026. Syntax and local storage tests have been validated. Real API calls, audio recording devices, Windows installer and complete GUI journeys have **not** been validated in this review. Do not treat it as a production application.

## Features

- Start a discovery manually from a problem statement and existing evidence.
- Optionally record a meeting, transcribe/analyze it, review extracted content, and populate discovery inputs.
- Work through evidence, hypotheses, experiments, an opportunity tree, and a Brief/PRD.
- Save local discovery sessions and revisit them.
- Configure an OpenAI API key stored in the operating-system credential vault through `keyring` (not in source files).

## Architecture

| Module | Purpose |
| --- | --- |
| `desktop_app.py` | Tkinter UI and orchestration |
| `meeting.py` | Local microphone capture and WAV export |
| `prompts.py` | Structured prompt templates for discovery and meeting analysis |
| `storage.py` | Local JSON persistence and discovery indexing |
| `settings_store.py` | Settings and OS keyring integration |

## Running on Windows

Requires **Python 3.11+** and an OpenAI API key belonging to the user.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python desktop_app.py
```

Configure the API key in the application's settings. API usage may incur charges. Test the source application before building an executable.

For packaging, use `build_windows.bat`. The build process requires Windows and PyInstaller; executable creation was not verified as part of this portfolio preparation.

## Validation

```bash
python -m compileall -q .
python -m unittest discover -s tests -v
```

Automated coverage is currently limited to storage safety and source syntax. It does not certify API results, GUI behavior, transcription quality or security.

## Responsible use and privacy

- Never include patient data or confidential company meeting recordings in this repository.
- Obtain participant consent before recording any meeting.
- Review AI-generated content; it can contain omissions or inaccuracies.
- Local data under the user's profile are **not encrypted** by this prototype; use non-sensitive demonstration content only.
- This repository has no open-source license attached. Public visibility does not grant reuse rights.
