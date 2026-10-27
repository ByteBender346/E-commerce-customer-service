import asyncio

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from dianshang.domain.messages import UserMessage, BotMessage, MessageType
from dianshang.domain.state import Turn
from dianshang.infrastructure.llm import llm
from dianshang.prompts.history_builder import HistoryBuilder
from dianshang.prompts.prompt_load import load_prompt


class ChitChatResponder:
    """闲聊回复：纯 LLM 生成，不检索业务知识。"""

    async def respond(self,
                      user_message: UserMessage,
                      recent_turns: list[Turn]) -> list[BotMessage]:
        rendered_user = HistoryBuilder._render_user_message(user_message)
        history = HistoryBuilder.build(recent_turns)

        prompt_text = load_prompt("chitchat_respond")
        prompt = PromptTemplate.from_template(prompt_text, template_format="jinja2")
        chain = prompt | llm | StrOutputParser()
        message = await chain.ainvoke({
            "user_message": rendered_user,
            "history": history,
        })
        return [BotMessage(text=message)]


if __name__ == '__main__':
    async def test():
        result = await ChitChatResponder().respond(
            UserMessage(sender_id="u1", message_id="m1", type=MessageType.TEXT, text="你好，在吗？"),
            [],
        )
        print(result[0].text)
    asyncio.run(test())
