---
name: summarization_skill
description: This skill summarizes conversation history using a local LLM via LiteLLM.
---

# Summarization Skill

## Description
This skill summarizes conversation history using a local LLM via LiteLLM.

## Configuration
- **API Key**: `LITELLM_API_KEY` (environment variable)
- **Base URL**: `http://127.0.0.1:4000`
- **Model**: `github_Copilot/gpt-4o`

## Dependencies
- `langchain_openai`
- `langchain_core`

## Usage
1. Import the function: `from skills.summarization_skill.summarize import summarize_conversation`
2. Prepare input: `messages = [{"role": "user", "content": "..."}, ...]`
3. Call: `summary = summarize_conversation(messages)`
