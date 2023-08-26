import openai

from lib.utils import try_get


class GPT:
    def __init__(self, api_key):
        assert (api_key is not None, "OpenAI API key must be supplied")
        openai.api_key = api_key

    def chat_completion(self, prompt):
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )
        return try_get(response, "choices", 0, "message", "content")
