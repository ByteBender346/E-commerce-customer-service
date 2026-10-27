import importlib
import inspect
import pkgutil

from dianshang.task.action.base import Action
from dianshang.task.action.builtin.action_listen import ActionListen
from dianshang.task.action.builtin.action_response import ActionResponse
from dianshang.task.action.custom.action_custom import ActionCustom
from dianshang.task.action.registry import ActionRegistry
from dianshang.task.action.runner import ActionRunner


def register_builtin_actions(runner: ActionRunner):
    runner.registry.register(ActionResponse())
    runner.registry.register(ActionListen())


def register_custom_actions(runner: ActionRunner):
    """注册自定义 Action，并自动扫描 custom 包下所有 Action 子类。"""
    runner.registry.register(ActionCustom())

    package = importlib.import_module("dianshang.task.action.custom")
    for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__, prefix=f"{package.__name__}."):
        if is_pkg:
            continue
        module = importlib.import_module(module_name)
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if not issubclass(obj, Action) or obj is Action:
                continue
            # 只注册在本模块中定义的类，避免重复导入
            if obj.__module__ != module.__name__:
                continue
            runner.registry.register(obj())


def build_action_runner() -> ActionRunner:
    runner = ActionRunner(ActionRegistry())
    register_builtin_actions(runner)
    register_custom_actions(runner)
    return runner


if __name__ == '__main__':
    runner = build_action_runner()
    print(f"已注册 {len(runner.registry._actions)} 个 Action")
    for name in runner.registry._actions:
        print(f"  - {name}")
