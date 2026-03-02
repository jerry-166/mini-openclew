from json.encoder import JSONEncoder

from langchain_core.messages import BaseMessage


class MessageJSONEncoder(JSONEncoder):
    """自定义 JSON 编码器，处理 langchain 消息对象"""
    def default(self, obj):
        # 处理 BaseMessage 子类（HumanMessage/SystemMessage 等）
        if isinstance(obj, BaseMessage):
            return {
                "type": obj.type,
                "content": obj.content,
                "additional_kwargs": obj.additional_kwargs,
                "response_metadata": obj.response_metadata
            }
        # 其他类型按默认规则处理
        return super().default(obj)