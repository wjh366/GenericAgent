"""
Skill自动生成模块
来源: Hermes Agent skills系统
功能: 任务完成后自动生成可复用技能
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class Skill:
    name: str
    description: str
    command: str  # 触发命令
    code: str  # 技能代码
    examples: List[str]
    tags: List[str]
    created_at: str
    usage_count: int = 0
    last_used: Optional[str] = None

class SkillGenerator:
    """
    自动从任务中提取技能
    
    工作流程:
    1. 任务执行时记录关键步骤
    2. 任务完成后分析生成Skill
    3. Skill存储到skills目录
    4. 下次遇到类似任务直接调用
    """
    
    def __init__(self, skills_dir: str = None):
        if skills_dir is None:
            skills_dir = os.path.join(os.path.dirname(__file__), "skills")
        self.skills_dir = skills_dir
        os.makedirs(skills_dir, exist_ok=True)
        self.skills: Dict[str, Skill] = {}
        self._load_skills()
    
    def _load_skills(self):
        """加载已有技能"""
        for fname in os.listdir(self.skills_dir):
            if fname.endswith('.json'):
                path = os.path.join(self.skills_dir, fname)
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    skill = Skill(**data)
                    self.skills[skill.name] = skill
    
    def _save_skill(self, skill: Skill):
        """保存技能到文件"""
        path = os.path.join(self.skills_dir, f"{skill.name}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(asdict(skill), f, ensure_ascii=False, indent=2)
    
    def record_task(self, task_id: str, description: str, steps: List[Dict]):
        """
        记录任务执行步骤
        
        steps格式: [{"action": "搜索", "result": "...", "code": "..."}]
        """
        self._current_task = {
            "id": task_id,
            "description": description,
            "steps": steps,
            "started_at": datetime.now().isoformat()
        }
    
    def add_step(self, action: str, result: Any, code: str = ""):
        """添加任务步骤"""
        if hasattr(self, '_current_task'):
            self._current_task["steps"].append({
                "action": action,
                "result": str(result)[:200],
                "code": code
            })
    
    def generate_skill(self, name: str, description: str, tags: List[str] = None) -> Skill:
        """
        从记录的任务生成技能
        
        从Hermes的skills目录结构学习:
        skills/
          name/
            skill.json  # 元数据
            impl.py     # 实现代码
            test.py     # 测试
        """
        if not hasattr(self, '_current_task'):
            raise ValueError("没有记录的任务，请先调用 record_task()")
        
        task = self._current_task
        
        # 生成技能代码
        code = self._generate_code(task)
        
        # 生成示例
        examples = self._generate_examples(task)
        
        # 创建技能
        skill = Skill(
            name=name,
            description=description,
            command=f"/{name.lower().replace(' ', '_')}",
            code=code,
            examples=examples,
            tags=tags or [],
            created_at=datetime.now().isoformat()
        )
        
        # 保存
        self.skills[name] = skill
        self._save_skill(skill)
        
        # 清理当前任务
        delattr(self, '_current_task')
        
        return skill
    
    def _generate_code(self, task: Dict) -> str:
        """从步骤生成可执行代码"""
        lines = [
            f'"""自动生成的技能: {task["description"]}"""',
            f'"""创建时间: {task["started_at"]}"""',
            "",
            "def execute(context: dict) -> dict:",
            '    """执行技能"""',
            "    results = []",
        ]
        
        for i, step in enumerate(task["steps"]):
            if step.get("code"):
                lines.append(f"    # 步骤 {i+1}: {step['action']}")
                # 简化代码，移除具体值
                code = step["code"]
                lines.append(f"    # {code[:100]}...")
                lines.append("")
        
        lines.extend([
            '    return {"success": True, "results": results}',
            "",
            "",
            'if __name__ == "__main__":',
            "    result = execute({})",
            "    print(result)"
        ])
        
        return "\n".join(lines)
    
    def _generate_examples(self, task: Dict) -> List[str]:
        """生成使用示例"""
        return [
            f"执行技能: {task['description']}",
            f"包含 {len(task['steps'])} 个步骤"
        ]
    
    def find_similar(self, description: str) -> List[Skill]:
        """查找相似技能"""
        desc_words = set(re.findall(r'\w+', description.lower()))
        scores = []
        
        for skill in self.skills.values():
            skill_words = set(re.findall(r'\w+', skill.description.lower()))
            common = desc_words & skill_words
            if common:
                scores.append((len(common), skill))
        
        scores.sort(reverse=True)
        return [s for _, s in scores[:3]]
    
    def invoke(self, name: str, context: Dict = None) -> Any:
        """调用技能"""
        if name not in self.skills:
            raise ValueError(f"未知技能: {name}")
        
        skill = self.skills[name]
        skill.usage_count += 1
        skill.last_used = datetime.now().isoformat()
        self._save_skill(skill)
        
        # 执行技能代码
        namespace = {}
        exec(skill.code, namespace)
        if 'execute' in namespace:
            return namespace['execute'](context or {})
        return {"success": True}
    
    def list_all(self) -> List[Dict]:
        """列出所有技能"""
        return [
            {
                "name": s.name,
                "description": s.description,
                "command": s.command,
                "usage_count": s.usage_count,
                "tags": s.tags
            }
            for s in self.skills.values()
        ]
    
    def help(self) -> str:
        """显示帮助"""
        lines = ["已学会的技能:"]
        for skill in self.skills.values():
            lines.append(f"  {skill.command} - {skill.description}")
            lines.append(f"    使用次数: {skill.usage_count}")
        return "\n".join(lines)


# 全局实例
skill_generator = SkillGenerator()


# === 使用示例 ===
if __name__ == "__main__":
    # 记录任务
    skill_generator.record_task(
        task_id="task_001",
        description="搜索并保存网页内容",
        steps=[
            {"action": "打开浏览器", "result": "成功"},
            {"action": "搜索关键词", "result": "找到10条结果"},
            {"action": "保存内容", "result": "已保存到文件"}
        ]
    )
    
    # 生成技能
    skill = skill_generator.generate_skill(
        name="web_search_save",
        description="搜索网页并保存结果",
        tags=["浏览器", "自动化"]
    )
    
    print(f"✅ 技能已生成: {skill.name}")
    print(f"命令: {skill.command}")
    print(f"\n技能代码预览:\n{skill.code[:500]}...")
