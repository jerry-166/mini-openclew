import os
import re
from typing import List, Dict, Any, Tuple, LiteralString


class SkillsManager:
    """技能管理器，负责扫描和管理Agent Skills"""

    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = skills_dir
        self.skills_snapshot_path = "SKILLS_SNAPSHOT.md"

    def scan_skills(self) -> List[Dict[str, str]]:
        """扫描技能目录，获取所有技能信息"""
        skills = []

        # 确保技能目录存在
        if not os.path.exists(self.skills_dir):
            return skills

        # 遍历技能目录
        for skill_name in os.listdir(self.skills_dir):
            skill_path = os.path.join(self.skills_dir, skill_name)
            if os.path.isdir(skill_path):
                skill_file = os.path.join(skill_path, "SKILL.md")
                if os.path.exists(skill_file):
                    # 读取SKILL.md文件，提取元数据
                    with open(skill_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    # 提取skill_name, Frontmatter中的描述
                    extracted_name, description = self._extract_name_description(content)

                    # 构建技能信息
                    skill_info = {
                        "name": extracted_name or skill_name,
                        "description": description or "无描述",
                        "location": f"./{self.skills_dir}/{skill_name}/SKILL.md"
                    }
                    skills.append(skill_info)

        return skills

    def _extract_name_description(self, content: str) -> tuple[LiteralString, LiteralString] | tuple[None, str] | str:
        """从SKILL.md内容中提取描述"""
        # 尝试从Frontmatter中提取
        frontmatter_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)  # dotall是包含换行符
        if frontmatter_match:
            frontmatter = frontmatter_match.group(1)
            name_match = re.search(r'name:\s*(.*)', frontmatter)
            description_match = re.search(r'description:\s*(.*)', frontmatter)
            if name_match and description_match:
                return name_match.group(1).strip(), description_match.group(1).strip()

        # 尝试从文件内容中提取第一行作为描述
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('---'):
                return None, line

        return "", ""

    def generate_skills_snapshot(self) -> str:
        """生成技能快照文件"""
        skills = self.scan_skills()

        # 构建快照内容
        snapshot_content = "<available_skills>\n"
        for skill in skills:
            snapshot_content += f"<skill>\n"
            snapshot_content += f"<name>{skill['name']}</name>\n"
            snapshot_content += f"<description>{skill['description']}</description>\n"
            snapshot_content += f"<location>{skill['location']}</location>\n"
            snapshot_content += "</skill>\n"
        snapshot_content += "</available_skills>"

        # 保存快照文件
        with open(self.skills_snapshot_path, "w", encoding="utf-8") as f:
            f.write(snapshot_content)

        return snapshot_content

    def get_skills_snapshot(self) -> str:
        """获取技能快照内容"""
        if os.path.exists(self.skills_snapshot_path):
            with open(self.skills_snapshot_path, "r", encoding="utf-8") as f:
                return f.read()
        else:
            return self.generate_skills_snapshot()
