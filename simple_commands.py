"""
简化命令系统
来源: Claude Code slash commands
功能: 自然语言命令简化，如 /search, /code, /git
"""

import re
from typing import Callable, Dict, List, Optional, Any
from dataclasses import dataclass
from functools import wraps

@dataclass
class Command:
    name: str
    description: str
    aliases: List[str]
    handler: Callable
    args_template: Optional[str] = None

class CommandRegistry:
    """命令注册器"""
    
    def __init__(self):
        self.commands: Dict[str, Command] = {}
        self.prefixes = ["/"]
    
    def register(
        self, 
        name: str, 
        description: str = "", 
        aliases: List[str] = None,
        args_template: str = None
    ):
        """装饰器注册命令"""
        def decorator(func: Callable) -> Callable:
            cmd = Command(
                name=name,
                description=description,
                aliases=aliases or [],
                handler=func,
                args_template=args_template
            )
            self.commands[name] = cmd
            for alias in cmd.aliases:
                self.commands[alias] = cmd
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def parse(self, text: str) -> Optional[tuple]:
        """解析命令，返回 (Command, args) 或 None"""
        text = text.strip()
        for prefix in self.prefixes:
            if text.startswith(prefix):
                parts = text[len(prefix):].split(None, 1)
                cmd_name = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                if cmd_name in self.commands:
                    return (self.commands[cmd_name], args)
        return None
    
    def execute(self, text: str, context: Dict[str, Any] = None) -> Any:
        """执行命令"""
        parsed = self.parse(text)
        if not parsed:
            return None
        
        cmd, args = parsed
        return cmd.handler(args, context or {})
    
    def help(self, cmd_name: str = None) -> str:
        """获取帮助"""
        if cmd_name:
            if cmd_name in self.commands:
                cmd = self.commands[cmd_name]
                help_text = f"/{cmd.name}"
                if cmd.aliases:
                    help_text += f" (别名: {', '.join('/'+a for a in cmd.aliases)})"
                help_text += "\n  " + cmd.description
                if cmd.args_template:
                    help_text += "\n  用法: /" + cmd.name + " " + cmd.args_template
                return help_text
            return f"未知命令: /{cmd_name}"
        
        # 列出所有命令
        lines = ["可用命令:"]
        for cmd in sorted(self.commands.values(), key=lambda c: c.name):
            if cmd.name == cmd.name.lower():  # 只显示主命令
                lines.append(f"  /{cmd.name} - {cmd.description}")
        return "\n".join(lines)


# 全局实例
registry = CommandRegistry()

# 快捷注册装饰器
def command(name: str, description: str = "", aliases: List[str] = None, args_template: str = None):
    return registry.register(name, description, aliases, args_template)


# === 内置命令 ===

@command(
    "search", 
    "搜索网络信息",
    aliases=["s", "g"],
    args_template="<关键词>"
)
def cmd_search(args: str, ctx: Dict) -> str:
    """搜索命令"""
    if not args:
        return "用法: /search <关键词>"
    return f"搜索: {args}\n(需要浏览器支持)"


@command(
    "git", 
    "Git操作",
    args_template="<add|commit|push|status|log> [参数]"
)
def cmd_git(args: str, ctx: Dict) -> str:
    """Git命令"""
    if not args:
        return "用法: /git <add|commit|push|status|log>"
    return f"Git {args}\n(需要实现Git操作)"


@command(
    "code", 
    "生成代码",
    aliases=["c"],
    args_template="<描述>"
)
def cmd_code(args: str, ctx: Dict) -> str:
    """代码生成命令"""
    if not args:
        return "用法: /code <描述你要的代码功能>"
    return f"生成代码: {args}\n(需要LLM支持)"


@command(
    "file", 
    "文件操作",
    args_template="<read|write|list> <路径> [内容]"
)
def cmd_file(args: str, ctx: Dict) -> str:
    """文件命令"""
    parts = args.split(None, 2)
    if len(parts) < 2:
        return "用法: /file <read|write|list> <路径> [内容]"
    action, path = parts[0], parts[1]
    content = parts[2] if len(parts) > 2 else ""
    return f"文件{action}: {path}"


@command(
    "help",
    "显示帮助信息",
    aliases=["h", "?"]
)
def cmd_help(args: str, ctx: Dict) -> str:
    """帮助命令"""
    return registry.help(args.strip() or None)


# === 交互式解析器 ===
class CommandParser:
    """命令解析器，支持混合自然语言"""
    
    def __init__(self, registry: CommandRegistry):
        self.registry = registry
    
    def process(self, text: str, context: Dict = None) -> Dict:
        """
        处理输入文本，返回:
        {
            "type": "command" | "natural",
            "command": command_name,
            "args": args,
            "original": original_text
        }
        """
        # 尝试解析命令
        parsed = self.registry.parse(text)
        if parsed:
            cmd, args = parsed
            return {
                "type": "command",
                "command": cmd.name,
                "args": args,
                "original": text
            }
        
        # 智能意图识别
        text_lower = text.lower().strip()
        
        # 搜索意图
        if any(kw in text_lower for kw in ["搜索", "查找", "search", "找"]):
            return {"type": "intent", "intent": "search", "query": text, "original": text}
        
        # Git意图
        if any(kw in text_lower for kw in ["git", "提交", "commit", "推送", "push"]):
            return {"type": "intent", "intent": "git", "query": text, "original": text}
        
        # 默认按自然语言处理
        return {"type": "natural", "query": text, "original": text}


if __name__ == "__main__":
    parser = CommandParser(registry)
    
    # 测试
    tests = ["/search Python教程", "/help", "/git status", "帮我写一个排序算法"]
    for t in tests:
        result = parser.process(t)
        print(f"输入: {t}")
        print(f"结果: {result}")
        print()
