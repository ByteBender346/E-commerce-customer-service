from pathlib import Path

import yaml

from dianshang.task.flow.models import FlowSlot, FlowsList, Flow
from dianshang.task.flow.steps import FlowStep, CollectSlotStep


class FlowLoader:
    """加载 user_flows.yml / system_flows.yml，解析为 FlowsList 对象。"""

    def load_many(self, paths: list[Path]) -> FlowsList:
        flows: list[Flow] = []
        slots: dict[str, FlowSlot] = {}
        for path in paths:
            result = self.load(path)
            flows.extend(result.flows)
            slots.update(result.slots)
        return FlowsList(flows=flows, slots=slots)

    def load(self, path: Path) -> FlowsList:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        slots = self._load_slots(data.get("slots", {}))
        flows = self._load_flows(data.get("flows", {}), slots)
        return FlowsList(flows=flows, slots=slots)

    @staticmethod
    def _load_slots(slot_data: dict[str, dict]) -> dict[str, FlowSlot]:
        return {name: FlowSlot(**info, name=name) for name, info in slot_data.items()}

    @staticmethod
    def _load_flows(flow_data: dict[str, dict], slots: dict[str, FlowSlot]) -> list[Flow]:
        flows = []
        for flow_id, info in flow_data.items():
            steps = [FlowStep.from_dict(s) for s in info["steps"]]
            # 收集该流程用到的槽位定义
            flow_slots = [slots[s.slot_name] for s in steps if isinstance(s, CollectSlotStep)]
            flows.append(Flow(
                id=flow_id,
                description=info.get("description", ""),
                name=info.get("name", ""),
                steps=steps,
                slots=flow_slots,
            ))
        return flows


if __name__ == '__main__':
    root = Path(__file__).parents[3]
    result = FlowLoader().load_many([
        root / "flow_config" / "user_flows.yml",
        root / "flow_config" / "system_flows.yml",
    ])
    print(f"共加载 {len(result.flows)} 个流程")
    for f in result.flows:
        print(f"  - {f.id}: {f.name}")
