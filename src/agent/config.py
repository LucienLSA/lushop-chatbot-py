"""
Agent 配置模块

本模块负责管理所有 Agent 的共享配置，包括：
- LLM 模型注册表（支持多供应商：OpenAI、Anthropic、xAI、Google）
- API 密钥配置和验证
- 模型初始化（默认模型、护栏模型、回退链）
- 中间件配置（重试、回退）

配置流程：
1. 从 .env 文件加载环境变量
2. 验证 API 密钥是否已设置
3. 根据可用的 API 密钥选择默认模型
4. 配置重试和回退中间件
"""
import logging
import os
from dataclasses import dataclass
from typing import Optional

import dotenv
from langchain.agents.middleware import ModelFallbackMiddleware
from langchain.chat_models import init_chat_model

from src.middleware.retry_middleware import ModelRetryMiddleware

dotenv.load_dotenv()

logger = logging.getLogger(__name__)


# =============================================================================
# 模型注册表
# =============================================================================


@dataclass
class ModelConfig:
    """
    模型配置数据类
    
    Attributes:
        id: 模型唯一标识符，格式为 "provider:model-name"
        name: 模型显示名称，用于日志和 UI
        provider: 供应商名称（xai、anthropic、openai、google）
        api_key_env: 对应的环境变量名称
        description: 模型描述（可选）
    """
    id: str
    name: str
    provider: str
    api_key_env: str
    description: Optional[str] = None


# 所有可用模型 - 单一数据源
MODELS: dict[str, ModelConfig] = {
    # xAI (Grok)
    "grok-4.1-fast": ModelConfig(
        id="xai:grok-4-1-fast-non-reasoning",
        name="Grok 4.1 Fast",
        provider="xai",
        api_key_env="XAI_API_KEY",
        description="Fast, optimized for tool calling",
    ),
    # Anthropic
    "claude-haiku": ModelConfig(
        id="anthropic:claude-haiku-4-5",
        name="Claude Haiku 4.5",
        provider="anthropic",
        api_key_env="ANTHROPIC_API_KEY",
        description="Fast and cost-effective",
    ),
    "claude-sonnet": ModelConfig(
        id="anthropic:claude-sonnet-4-5",
        name="Claude Sonnet 4.5",
        provider="anthropic",
        api_key_env="ANTHROPIC_API_KEY",
        description="Balanced performance",
    ),
    "claude-opus": ModelConfig(
        id="anthropic:claude-opus-4-5",
        name="Claude Opus 4.5",
        provider="anthropic",
        api_key_env="ANTHROPIC_API_KEY",
        description="Most capable Anthropic model",
    ),
    # OpenAI
    "gpt-5-nano": ModelConfig(
        id="openai:gpt-5-nano",
        name="GPT-5 Nano",
        provider="openai",
        api_key_env="OPENAI_API_KEY",
        description="Fastest, most economical",
    ),
    "gpt-5-mini": ModelConfig(
        id="openai:gpt-5-mini",
        name="GPT-5 Mini",
        provider="openai",
        api_key_env="OPENAI_API_KEY",
        description="Fast and capable",
    ),
    "gpt-5": ModelConfig(
        id="openai:gpt-5",
        name="GPT-5",
        provider="openai",
        api_key_env="OPENAI_API_KEY",
        description="Most capable OpenAI model",
    ),
    # Google
    "gemini-2.5-flash": ModelConfig(
        id="google_genai:gemini-2.5-flash",
        name="Gemini 2.5 Flash",
        provider="google",
        api_key_env="GOOGLE_API_KEY",
        description="Fast and capable Google model",
    ),
    "gemini-3-flash": ModelConfig(
        id="google_genai:gemini-3-flash-preview",
        name="Gemini 3 Flash",
        provider="google",
        api_key_env="GOOGLE_API_KEY",
        description="Latest Gemini 3 Flash model",
    ),
    "gemini-3-pro": ModelConfig(
        id="google_genai:gemini-3-pro-preview",
        name="Gemini 3 Pro",
        provider="google",
        api_key_env="GOOGLE_API_KEY",
        description="Most capable Gemini model",
    ),
}

# 模型优先级顺序（第一个可用的模型会被选中）
_DEFAULT_MODEL_ORDER = ["claude-haiku", "grok-4.1-fast", "gpt-5-mini", "claude-sonnet", "gemini-2.5-flash"]
_GUARDRAILS_MODEL_ORDER = ["grok-4.1-fast", "claude-haiku", "gpt-5-mini", "claude-sonnet", "gemini-2.5-flash"]
_FALLBACK_CHAIN_ORDER = [
    MODELS["claude-haiku"],
    MODELS["grok-4.1-fast"],
    MODELS["gpt-5-mini"],
    MODELS["claude-sonnet"],
]


# =============================================================================
# API 密钥配置
# =============================================================================

# 需要检查的 API 密钥列表
API_KEYS = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENROUTER_API_KEY",
    "XAI_API_KEY",
    "GOOGLE_API_KEY",
]

# 清理并设置 API 密钥（去除空白字符）
for key in API_KEYS:
    if value := os.getenv(key):
        os.environ[key] = value.strip()
        logger.info(f"{key} configured")


def _has_api_key(model_config: ModelConfig) -> bool:
    """
    检查模型的 API 密钥是否已配置
    
    Args:
        model_config: 模型配置对象
        
    Returns:
        如果 API 密钥已设置且非空则返回 True
    """
    return bool(os.getenv(model_config.api_key_env, "").strip())


def _first_available(order: list[str]) -> Optional[ModelConfig]:
    """
    从优先级列表中返回第一个可用的模型
    
    Args:
        order: 模型名称的优先级列表
        
    Returns:
        第一个有可用 API 密钥的模型配置，如果没有则返回 None
    """
    for key in order:
        m = MODELS[key]
        if _has_api_key(m):
            return m
    return None


def _filter_available(model_list: list[ModelConfig]) -> list[ModelConfig]:
    """
    过滤出所有可用的模型
    
    Args:
        model_list: 模型配置列表
        
    Returns:
        有可用 API 密钥的模型列表
    """
    return [m for m in model_list if _has_api_key(m)]


# 根据配置的供应商解析默认模型和护栏模型
_resolved_default = _first_available(_DEFAULT_MODEL_ORDER)
if _resolved_default is None:
    raise RuntimeError(
        "No LLM API key is set. Set at least one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, XAI_API_KEY, GOOGLE_API_KEY. "
        "See .env.example for details."
    )
DEFAULT_MODEL = _resolved_default

_resolved_guardrails = _first_available(_GUARDRAILS_MODEL_ORDER)
GUARDRAILS_MODEL = _resolved_guardrails if _resolved_guardrails is not None else DEFAULT_MODEL
if _resolved_guardrails is None:
    logger.info(f"No separate guardrails key; using default model for guardrails: {GUARDRAILS_MODEL.name}")

FALLBACK_MODELS = _filter_available(_FALLBACK_CHAIN_ORDER)
if not FALLBACK_MODELS:
    FALLBACK_MODELS = [DEFAULT_MODEL]
    logger.info("Fallback chain has only one model (no other API keys configured)")

# =============================================================================
# 模型初始化
# =============================================================================

# 重试配置
MAX_RETRIES = int(os.getenv("MODEL_MAX_RETRIES", "2"))

# 主可配置模型（可在运行时切换）
configurable_model = init_chat_model(
    model=DEFAULT_MODEL.id,
    configurable_fields=("model",),
)
logger.info(f"Default model: {DEFAULT_MODEL.name} ({DEFAULT_MODEL.id})")

# Anthropic 优化模型（带缓存，仅当 Anthropic 密钥设置时）
anthropic_configurable_model = None
if _has_api_key(MODELS["claude-sonnet"]):
    anthropic_configurable_model = init_chat_model(
        model=MODELS["claude-sonnet"].id,
        configurable_fields=("model",),
    )


# =============================================================================
# 中间件配置
# =============================================================================

# 重试中间件：当模型调用失败时自动重试
model_retry_middleware = ModelRetryMiddleware(max_retries=MAX_RETRIES)

# 回退中间件：当主模型失败时自动切换到备用模型
model_fallback_middleware = ModelFallbackMiddleware(*[m.id for m in FALLBACK_MODELS])
logger.info(f"Fallback chain: {' -> '.join(m.name for m in FALLBACK_MODELS)}")


# =============================================================================
# 模块导出
# =============================================================================

__all__ = [
    # 模型
    "MODELS",
    "DEFAULT_MODEL",
    "GUARDRAILS_MODEL",
    "FALLBACK_MODELS",
    "ModelConfig",
    # 可配置模型
    "configurable_model",
    "anthropic_configurable_model",
    # 中间件
    "model_retry_middleware",
    "model_fallback_middleware",
    # 配置
    "MAX_RETRIES",
    "logger",
]
