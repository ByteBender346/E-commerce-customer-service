from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from dianshang.domain.messages import UserMessage, BotMessage
from dianshang.domain.state import Turn
from dianshang.infrastructure.llm import llm
from dianshang.knowledge.providers import KnowledgeChunk
from dianshang.prompts.history_builder import HistoryBuilder
from dianshang.prompts.prompt_load import load_prompt


class KnowledgeResponder:
    """将检索到的知识片段交给 LLM，生成自然语言回复。"""

    async def respond(self,
                      user_message: UserMessage,
                      recent_turns: list[Turn],
                      chunks: list[KnowledgeChunk]) -> list[BotMessage]:
        rendered_user = HistoryBuilder._render_user_message(user_message)
        history = HistoryBuilder.build(recent_turns)
        knowledge_content = "\n\n".join(c.content for c in chunks)

        prompt_text = load_prompt("knowledge_respond")
        prompt = PromptTemplate.from_template(prompt_text, template_format="jinja2")
        chain = prompt | llm | StrOutputParser()
        message = await chain.ainvoke({
            "user_message": rendered_user,
            "history": history,
            "knowledge_content": knowledge_content,
        })
        return [BotMessage(text=message)]
