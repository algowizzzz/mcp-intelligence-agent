"""
LLM factory — returns the configured chat model based on LLM_PROVIDER env var
or the persisted config at sajhamcpserver/config/llm_config.json.

Supported providers:
  anthropic   — Claude via Anthropic API (default)
  huggingface — Llama / other models via HuggingFace Inference API (OpenAI-compat)
  xai         — Grok via xAI API (OpenAI-compat, base_url https://api.x.ai/v1)
  bedrock     — Claude on AWS Bedrock (requires: pip install langchain-aws boto3)

Config precedence (highest → lowest):
  1. sajhamcpserver/config/llm_config.json  (set via Super Admin UI)
  2. Environment variables (.env)
"""
import json
import os
import pathlib

_CONFIG_PATH = pathlib.Path(__file__).parent.parent / 'sajhamcpserver' / 'config' / 'llm_config.json'


def _load_file_config() -> dict:
    """Load llm_config.json. Returns empty dict if missing or invalid."""
    try:
        if _CONFIG_PATH.exists():
            return json.loads(_CONFIG_PATH.read_text())
    except Exception:
        pass
    return {}


def create_llm():
    file_cfg = _load_file_config()

    # Active provider: file config wins over env var
    provider = file_cfg.get('provider') or os.getenv('LLM_PROVIDER', 'anthropic')

    if provider == 'anthropic':
        from langchain_anthropic import ChatAnthropic
        prov_cfg = file_cfg.get('anthropic', {})
        api_key = prov_cfg.get('api_key') or os.getenv('ANTHROPIC_API_KEY')
        model   = prov_cfg.get('model')    or os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')
        max_tok = prov_cfg.get('max_tokens') or int(os.getenv('LLM_MAX_TOKENS', '8192'))
        return ChatAnthropic(
            model=model,
            api_key=api_key,
            temperature=0,
            streaming=True,
            max_tokens=int(max_tok),
        )

    elif provider == 'xai':
        from langchain_openai import ChatOpenAI
        prov_cfg = file_cfg.get('xai', {})
        api_key = prov_cfg.get('api_key') or os.getenv('XAI_API_KEY')
        if not api_key:
            raise ValueError("XAI_API_KEY is required when LLM_PROVIDER=xai")
        model   = prov_cfg.get('model')      or os.getenv('XAI_MODEL', 'grok-3')
        max_tok = prov_cfg.get('max_tokens') or int(os.getenv('LLM_MAX_TOKENS', '8192'))
        return ChatOpenAI(
            model=model,
            base_url='https://api.x.ai/v1',
            api_key=api_key,
            temperature=0,
            streaming=True,
            max_tokens=int(max_tok),
        )

    elif provider == 'huggingface':
        from langchain_openai import ChatOpenAI
        prov_cfg = file_cfg.get('huggingface', {})
        api_key = prov_cfg.get('api_key') or os.getenv('HF_API_KEY')
        if not api_key:
            raise ValueError("HF_API_KEY is required when LLM_PROVIDER=huggingface")
        model   = prov_cfg.get('model')      or os.getenv('HF_MODEL', 'meta-llama/Llama-3.3-70B-Instruct')
        max_tok = prov_cfg.get('max_tokens') or int(os.getenv('LLM_MAX_TOKENS', '4096'))
        return ChatOpenAI(
            model=model,
            base_url='https://router.huggingface.co/v1',
            api_key=api_key,
            temperature=0,
            streaming=True,
            max_tokens=int(max_tok),
        )

    elif provider == 'bedrock':
        prov_cfg = file_cfg.get('bedrock', {})
        model_id = prov_cfg.get('model_id') or os.getenv(
            'BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-20250514-v1:0'
        )
        region   = prov_cfg.get('region') or os.getenv('AWS_REGION', 'us-east-1')
        max_tok  = prov_cfg.get('max_tokens') or int(os.getenv('LLM_MAX_TOKENS', '8192'))
        try:
            from langchain_aws import ChatBedrockConverse
        except ImportError:
            raise ImportError(
                "Bedrock provider requires: pip install langchain-aws boto3"
            )
        return ChatBedrockConverse(
            model=model_id,
            region_name=region,
            temperature=0,
            streaming=True,
            max_tokens=int(max_tok),
        )

    else:
        raise ValueError(
            f"Unknown LLM provider: '{provider}'. "
            "Valid options: 'anthropic', 'xai', 'huggingface', 'bedrock'."
        )
