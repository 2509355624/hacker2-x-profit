from django.conf import settings

VOLCANO_API_KEY = settings.VOLCANO_API_KEY
VOLCANO_BASE_URL = settings.VOLCANO_BASE_URL


class AIConfig:
    MODEL_MAPPING = {
        'deepseek-r1': {
            'model': 'deepseek-r1-250528',
            'base_url': VOLCANO_BASE_URL,
            'api_key': VOLCANO_API_KEY
        },
        'Doubao-Seed-2.0-lite': {
            'model': 'doubao-seed-2-0-lite-260215',
            'base_url': VOLCANO_BASE_URL,
            'api_key': VOLCANO_API_KEY
        }
    }

    MODEL_PARAMETERS = {
        'temperature': 0
    }

    @classmethod
    def get_model_config(cls, model_name: str = 'deepseek-r1-250528'):
        config = cls.MODEL_MAPPING[model_name].copy()
        return config

    @classmethod
    def get_model_parameters(cls):
        return cls.MODEL_PARAMETERS.copy()
