"""
LLM factory — returns the configured chat model based on LLM_PROVIDER env var.

Supported providers:
  anthropic   — Claude via Anthropic API (default)
  huggingface — Llama / other models via HuggingFace Inference API (OpenAI-compat)
  xai         — Grok via xAI API (OpenAI-compat, base_url https://api.x.ai/v1)
  bedrock     — Claude on AWS Bedrock (stubbed; uncomment block to activate)

To switch to xAI Grok:
  1. Set LLM_PROVIDER=xai in .env
  2. Set XAI_API_KEY=xai-... in .env
  3. Optionally set XAI_MODEL (default: grok-3)
"""
import os


def create_llm():
    provider = os.getenv('LLM_PROVIDER', 'anthropic')

    if provider == 'anthropic':
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514'),
            temperature=0,
            streaming=True,
            max_tokens=int(os.getenv('LLM_MAX_TOKENS', '8192')),
        )

    elif provider == 'huggingface':
        from langchain_openai import ChatOpenAI
        hf_key = os.getenv('HF_API_KEY')
        if not hf_key:
            raise ValueError("HF_API_KEY is required when LLM_PROVIDER=huggingface")
        model = os.getenv('HF_MODEL', 'meta-llama/Llama-3.3-70B-Instruct')
        return ChatOpenAI(
            model=model,
            base_url='https://router.huggingface.co/v1',
            api_key=hf_key,
            temperature=0,
            streaming=True,
            max_tokens=int(os.getenv('LLM_MAX_TOKENS', '4096')),
        )

    elif provider == 'xai':
        from langchain_openai import ChatOpenAI
        xai_key = os.getenv('XAI_API_KEY')
        if not xai_key:
            raise ValueError("XAI_API_KEY is required when LLM_PROVIDER=xai")
        model = os.getenv('XAI_MODEL', 'grok-3')
        return ChatOpenAI(
            model=model,
            base_url='https://api.x.ai/v1',
            api_key=xai_key,
            temperature=0,
            streaming=True,
            max_tokens=int(os.getenv('LLM_MAX_TOKENS', '8192')),
        )

    elif provider == 'bedrock':
        # Uncomment after: pip install langchain-aws boto3
        # from langchain_aws import ChatBedrockConverse
        # return ChatBedrockConverse(
        #     model=os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-20250514-v1:0'),
        #     region_name=os.getenv('AWS_REGION', 'us-east-1'),
        #     temperature=0,
        #     streaming=True,
        # )
        raise NotImplementedError(
            "Bedrock provider is stubbed. Uncomment the langchain-aws block in "
            "agent/llm_factory.py and install: pip install langchain-aws boto3"
        )

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: '{provider}'. "
            "Valid options: 'anthropic', 'huggingface', 'xai', 'bedrock'."
        )
