"""
插件系统
来源: Claude Code plugins + Hermes plugins
功能: 支持自定义命令、Agent、Hook的插件化扩展
"""

import os
import json
from typing import Dict, List, Callable, Any

class PluginRegistry:
    """插件注册表"""
    def __init__(self):
        self.plugins: Dict = {}
        self.hooks: Dict[str, List[Callable]] = {}
    
    def register(self, plugin: Dict) -> None:
        """注册插件"""
        self.plugins[plugin["name"]] = plugin
    
    def get(self, name: str) -> Dict:
        """获取插件"""
        return self.plugins.get(name)
    
    def list(self) -> List[Dict]:
        """列出所有插件"""
        return list(self.plugins.values())
    
    def register_hook(self, hook_name: str, callback: Callable) -> None:
        """注册钩子"""
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []
        self.hooks[hook_name].append(callback)
    
    def trigger_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """触发钩子"""
        results = []
        if hook_name in self.hooks:
            for callback in self.hooks[hook_name]:
                try:
                    results.append(callback(*args, **kwargs))
                except Exception as e:
                    print(f"Hook error: {e}")
        return results

# 全局注册表
plugin_registry = PluginRegistry()

class BuiltInHooks:
    """内置钩子点"""
    ON_STARTUP = "on_startup"
    ON_SHUTDOWN = "on_shutdown"
    ON_MESSAGE = "on_message"
    ON_ERROR = "on_error"

def register_plugin(name: str, version: str, description: str,
                   commands: List = None, agents: List = None, hooks: List = None) -> None:
    """注册插件装饰器"""
    def decorator(func):
        plugin = {
            "name": name,
            "version": version,
            "description": description,
            "commands": commands or [],
            "agents": agents or [],
            "hooks": hooks or [],
            "enabled": True,
            "main": func
        }
        plugin_registry.register(plugin)
        return func
    return decorator

if __name__ == "__main__":
    # 测试
    print("Plugin system loaded")
    print(f"Built-in hooks: {[attr for attr in dir(BuiltInHooks) if not attr.startswith('_')]}")
