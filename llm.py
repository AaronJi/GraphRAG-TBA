"""The OpenAI Chat Completions client used by online queries."""

import hashlib
import json
import os
from tempfile import NamedTemporaryFile

from dotenv import load_dotenv
from openai import OpenAI
import tiktoken
import yaml


def extract_json(text):
    decoder = json.JSONDecoder()
    for position, character in enumerate(text or ""):
        if character == "{":
            try:
                obj, _ = decoder.raw_decode(text[position:])
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                return obj
    raise ValueError("Response contains no JSON object")


class Client:
    def __init__(self, root, cache):
        load_dotenv(root / ".env")
        key = os.getenv("OPENAI_API_KEY")
        if key in (None, "", "your_openai_api_key"):
            raise ValueError("Set OPENAI_API_KEY in the environment or .env")
        config = yaml.safe_load((root / "settings.yaml").read_text(encoding="utf-8"))
        self.settings = config["llm"]
        self.endpoint = os.path.expandvars(self.settings["api_base"])
        self.client = OpenAI(api_key=key, base_url=self.endpoint,
                             timeout=self.settings["request_timeout"], max_retries=self.settings["max_retries"])
        self.encoding = tiktoken.get_encoding(config["encoding_model"])
        self.cache = cache
        self.cache.mkdir(parents=True, exist_ok=True)

    def call(self, stage, messages, validate, max_tokens):
        request = {
            "model": self.settings["model"],
            "messages": messages,
            "temperature": self.settings["temperature"],
            "max_completion_tokens": max_tokens,
            "reasoning_effort": "none",
        }
        estimated = sum(len(self.encoding.encode(m["content"])) + 8 for m in messages) + 16
        if estimated + max_tokens > 16000:
            raise ValueError(f"Context budget exceeded in {stage}")
        key = hashlib.sha256(json.dumps([self.endpoint, stage, request], sort_keys=True).encode()).hexdigest()
        path = self.cache / f"{key}.json"
        if path.is_file():
            result = json.loads(path.read_text(encoding="utf-8"))
            validate(result)
            return result

        for attempt in range(2):
            choice = self.client.chat.completions.create(**request).choices[0]
            try:
                if choice.finish_reason == "length":
                    raise ValueError("Output truncated")
                result = extract_json(choice.message.content)
                validate(result)
            except (ValueError, TypeError, KeyError) as error:
                if attempt:
                    raise ValueError(f"Invalid response in {stage}: {error}") from error
                request["messages"] = messages + [{
                    "role": "user",
                    "content": "Your previous response failed validation. Return only the complete JSON object with the required keys, numeric scores, and exact IDs. Be concise.",
                }]
                continue
            # A valid result survives interruption without leaving a partial cache entry.
            with NamedTemporaryFile("w", dir=self.cache, encoding="utf-8", delete=False) as stream:
                json.dump(result, stream, ensure_ascii=False)
            os.replace(stream.name, path)
            return result
