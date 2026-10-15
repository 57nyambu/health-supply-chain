import base64
import json

import requests
from django.conf import settings


class GemmaClientError(Exception):
    pass


class GemmaClient:
    BASE = 'https://generativelanguage.googleapis.com/v1beta/models'

    def __init__(self, model=None):
        self.model = model or settings.GEMMA_MODEL_ASSISTANT
        self.key = settings.GEMMA_API_KEY

    def _post(self, payload):
        if not self.key:
            raise GemmaClientError('GEMMA_API_KEY is not configured.')

        response = requests.post(
            f'{self.BASE}/{self.model}:generateContent?key={self.key}',
            json=payload,
            timeout=30,
        )
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            raise GemmaClientError(f'Gemma request failed: {exc}') from exc
        return response.json()

    @staticmethod
    def extract_text(raw):
        candidates = raw.get('candidates', [])
        if not candidates:
            return ''

        content = candidates[0].get('content', {})
        parts = content.get('parts', [])
        lines = [part.get('text', '') for part in parts if part.get('text')]
        return '\n'.join(lines).strip()

    def generate_text(self, prompt):
        payload = {
            'contents': [{'parts': [{'text': prompt}]}],
        }
        raw = self._post(payload)
        return self.extract_text(raw)

    def generate_vision_json(self, image_file, prompt):
        encoded = base64.b64encode(image_file.read()).decode('utf-8')
        mime_type = getattr(image_file, 'content_type', 'image/jpeg') or 'image/jpeg'

        payload = {
            'contents': [
                {
                    'parts': [
                        {'text': prompt},
                        {'inline_data': {'mime_type': mime_type, 'data': encoded}},
                    ]
                }
            ]
        }

        raw = self._post(payload)
        text = self.extract_text(raw)
        if not text:
            raise GemmaClientError('Gemma vision response was empty.')

        normalized = text.strip().strip('`')
        if normalized.startswith('json'):
            normalized = normalized[4:].strip()

        try:
            return json.loads(normalized)
        except json.JSONDecodeError as exc:
            raise GemmaClientError('Gemma vision response is not valid JSON.') from exc
