import os
from typing import List, Dict, Any

import tiktoken


class MemoryManager:
    """记忆管理器，负责系统提示词拼接和记忆管理"""

    def __init__(self, workspace_dir: str = "workspace", memory_dir: str = "memory"):
        self.workspace_dir = workspace_dir
        self.memory_dir = memory_dir
        self.max_token_length = 4096  # 默认Token限制

    def get_system_prompt(self) -> str:
        """获取完整的系统提示词"""
        # 1. 读取SKILLS_SNAPSHOT.md
        skills_snapshot = self._read_file("SKILLS_SNAPSHOT.md")

        # 2. 读取SOUL.md
        soul = self._read_file(os.path.join(self.workspace_dir, "SOUL.md"))

        # 3. 读取IDENTITY.md
        identity = self._read_file(os.path.join(self.workspace_dir, "IDENTITY.md"))

        # 4. 读取USER.md
        user = self._read_file(os.path.join(self.workspace_dir, "USER.md"))

        # 5. 读取AGENTS.md
        agents = self._read_file(os.path.join(self.workspace_dir, "AGENTS.md"))

        # 6. 读取MEMORY.md
        memory = self._read_file(os.path.join(self.memory_dir, "MEMORY.md"))

        # 拼接系统提示词
        system_prompt = f"{skills_snapshot}\n\n{soul}\n\n{identity}\n\n{user}\n\n{agents}\n\n{memory}"

        # 处理Token截断
        system_prompt = self._truncate_prompt(system_prompt)

        return system_prompt

    def _read_file(self, file_path: str) -> str:
        """读取文件内容"""
        try:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            return ""
        except Exception as e:
            print(f"读取文件失败 {file_path}: {e}")
            return ""

    def _truncate_prompt(self, prompt: str) -> str:
        """截断过长的提示词"""
        max_chars = self.max_token_length * 4  # 假设平均每个Token对应4个字符
        encoding = tiktoken.encoding_for_model(model_name="gpt-4o")
        token = encoding.encode(prompt)
        if len(token) > max_chars:
            return prompt[:max_chars] + "\n...[truncated]"
        return prompt

    def update_memory(self, content: str):
        """更新记忆文件"""
        memory_file = os.path.join(self.memory_dir, "MEMORY.md")
        try:
            with open(memory_file, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"更新记忆失败: {e}")
            return False

    def get_memory(self) -> str:
        """获取记忆内容"""
        return self._read_file(os.path.join(self.memory_dir, "MEMORY.md"))
