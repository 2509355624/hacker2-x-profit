from django.conf import settings

DOUBAO_API_KEY = settings.DOUBAO_API_KEY
DOUBAO_BASE_URL = settings.DOUBAO_BASE_URL


class AIConfig:
    MODEL_MAPPING = {
        'deepseek-r1': {
            'model': 'deepseek-r1-250528',
            'base_url': DOUBAO_BASE_URL,
            'api_key': DOUBAO_API_KEY
        }
    }

    MODEL_PARAMETERS = {
        'temperature': 0
    }

    @classmethod
    def get_model_config(cls, model_name: str = 'deepseek-r1'):
        config = cls.MODEL_MAPPING[model_name].copy()
        return config

    @classmethod
    def get_model_parameters(cls):
        return cls.MODEL_PARAMETERS.copy()
