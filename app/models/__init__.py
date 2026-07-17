# 导入所有模型，确保 SQLAlchemy 关系解析正常
# 顺序：先定义被依赖的模型

from app.models.base import Base
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document, DocumentStatus
from app.models.chunk import Chunk
from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageRole
from app.models.feedback import Feedback
from app.models.mineru_asset import DocumentImage, DocumentTable
from app.models.memory import MemoryFact, UserPreference
from app.models.prompt import PromptItem
