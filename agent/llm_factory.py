"""
LLM factory — returns the configured chat model based on LLM_PROVIDER env var.
Set LLM_PROVIDER=bedrock and uncomment the bedrock block to switch to AWS Bedrock.
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
        raise ValueError(f"Unknown LLM_PROVIDER: '{provider}'. Set to 'anthropic' or 'bedrock'.")
