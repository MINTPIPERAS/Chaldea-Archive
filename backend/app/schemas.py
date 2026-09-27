from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiConfigIn(BaseModel):
    name: str
    provider_kind: str = "openai-compatible"
    base_url: str | None = None
    api_key: str | None = None
    model: str
    temperature: float = 0.7
    max_tokens: int | None = None
    system_prompt: str | None = None
    is_default: bool = False


class ApiConfigOut(ApiConfigIn):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ConversationCreate(BaseModel):
    title: str = "新对话"


class ConversationRename(BaseModel):
    title: str


class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageOut(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    status: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseModel):
    content: str = Field(min_length=1)
    conversation_id: int | None = None
    api_config_id: int | None = None


class TestConfigRequest(BaseModel):
    """测试连通性：传 id 用已存配置，否则用表单当前值。"""

    id: int | None = None
    provider_kind: str = "openai-compatible"
    base_url: str | None = None
    api_key: str | None = None
    model: str = ""
