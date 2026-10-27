from dianshang.domain.messages import BotMessage
from dianshang.domain.state import DialogueState
from dianshang.task.action.runner import ActionRunner
from dianshang.task.command.models import Command
from dianshang.task.command.processor import CommandProcessor
from dianshang.task.flow.executor import FlowExecutor
from dianshang.task.flow.models import FlowsList


class TaskHandler:
    """业务任务入口：先执行命令（启动/暂停/恢复/取消流程），再推进流程执行。"""

    def __init__(self,
                 command_processor: CommandProcessor,
                 flows: FlowsList,
                 flow_executor: FlowExecutor,
                 action_runner: ActionRunner):
        self.command_processor = command_processor
        self.flows = flows
        self.flow_executor = flow_executor
        self.action_runner = action_runner

    async def handle(self, commands: list[Command], state: DialogueState) -> list[BotMessage]:
        self.command_processor.run(commands, state, self.flows)
        return await self.flow_executor.run_task(state, self.action_runner, self.flows)
