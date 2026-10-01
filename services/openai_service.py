import os

from flask import current_app, has_app_context

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class OpenAIServiceError(Exception):
    """Raised when the chatbot cannot get a usable OpenAI response."""

    pass


class OpenAIService:
    def __init__(self, api_key=None, model=None):
        self.api_key = api_key or self._config_value("OPENAI_API_KEY")
        self.model = model or self._config_value("OPENAI_MODEL", "gpt-4o-mini")
        self.timeout = float(self._config_value("OPENAI_TIMEOUT_SECONDS", "30"))
        self.max_output_tokens = int(self._config_value("OPENAI_MAX_OUTPUT_TOKENS", "1200"))

        if not self.api_key:
            raise OpenAIServiceError(
                "OpenAI API key is not configured. Add OPENAI_API_KEY to your .env file."
            )

        if OpenAI is None:
            raise OpenAIServiceError(
                "The OpenAI Python package is not installed. Run: pip install openai"
            )

        try:
            self.client = OpenAI(api_key=self.api_key, timeout=self.timeout)
        except Exception as error:
            raise OpenAIServiceError("Unable to initialize the OpenAI client.") from error

    def generate_reply(self, message, history):
        """Generate one assistant reply using recent session history."""
        if not isinstance(message, str) or not message.strip():
            raise OpenAIServiceError("Message is required.")

        response_input = self._build_response_input(message, history)

        try:
            return self._generate_with_responses_api(response_input)
        except Exception as error:
            if self._should_try_chat_fallback(error):
                try:
                    return self._generate_with_chat_completions(response_input)
                except Exception as fallback_error:
                    raise OpenAIServiceError(
                        "OpenAI request failed. Check your API key, model, billing, and network connectivity."
                    ) from fallback_error

            raise OpenAIServiceError(
                "OpenAI request failed. Check your API key, model, billing, and network connectivity."
            ) from error

    def _build_response_input(self, message, history):
        developer_prompt = (
            "You are NomadX AI, a professional travel assistant running inside a Flask travel platform. "
            "Answer naturally like ChatGPT while staying practical, friendly, and safety-aware. "
            "Maintain context across turns. Help with travel planning, hotels, restaurants, rentals, maps, "
            "weather, emergencies, bookings, documents, itineraries, and general questions. "
            "Use clear formatting for long answers and ask a short follow-up only when needed."
        )

        messages = [{"role": "developer", "content": developer_prompt}]

        for turn in history[-20:]:
            if isinstance(turn, dict) and turn.get("role") in {"user", "assistant"} and isinstance(turn.get("content"), str):
                messages.append({"role": turn["role"], "content": turn["content"]})

        messages.append({"role": "user", "content": message})
        return messages

    def _generate_with_responses_api(self, response_input):
        # The Responses API is the current OpenAI SDK surface for conversational apps.
        response = self.client.responses.create(
            model=self.model,
            input=response_input,
            max_output_tokens=self.max_output_tokens,
        )
        assistant_message = (response.output_text or "").strip()
        if not assistant_message:
            raise OpenAIServiceError("The AI did not return a reply.")
        return assistant_message

    def _generate_with_chat_completions(self, response_input):
        # Compatibility path for models/accounts that still expect chat completions.
        chat_messages = [
            {
                "role": "system" if item["role"] == "developer" else item["role"],
                "content": item["content"],
            }
            for item in response_input
        ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=chat_messages,
            temperature=0.6,
            max_tokens=self.max_output_tokens,
        )
        assistant_message = (response.choices[0].message.content or "").strip()
        if not assistant_message:
            raise OpenAIServiceError("The AI did not return a reply.")
        return assistant_message

    def _should_try_chat_fallback(self, error):
        message = str(error).lower()
        fallback_markers = ("responses", "unsupported", "not found", "invalid type", "unknown parameter")
        return any(marker in message for marker in fallback_markers)

    def _config_value(self, name, default=None):
        if has_app_context():
            return current_app.config.get(name) or os.environ.get(name, default)
        return os.environ.get(name, default)
