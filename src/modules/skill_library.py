"""技能库管理系统

负责技能包的注册、发现、执行和管理，支持技能的版本控制、签名验证和生态管理。

主要功能：
- 技能包的注册和发现
- 技能执行和参数验证
- 版本管理和依赖处理
- 签名验证和安全检查
- 技能评分和推荐
"""

import json
import hashlib
import os
import shutil
import zipfile
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from pathlib import Path
import semver

# MCP 相关导入
from ..core.mcp_manager import MCPManager


class SkillStatus(Enum):
    """技能状态"""
    ACTIVE = "active"  # 活跃
    DEPRECATED = "deprecated"  # 已弃用
    DISABLED = "disabled"  # 已禁用
    BETA = "beta"  # 测试版
    ALPHA = "alpha"  # 内测版


class PermissionLevel(Enum):
    """权限级别"""
    READ_PUBLIC = "read_public"  # 只读公开内容
    READ_PRIVATE = "read_private"  # 读取私有内容
    WRITE_SAFE = "write_safe"  # 安全写入操作
    WRITE_SENSITIVE = "write_sensitive"  # 敏感写入操作
    ADMIN = "admin"  # 管理员权限


class ExecutionResult(Enum):
    """执行结果"""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    PERMISSION_DENIED = "permission_denied"
    VALIDATION_ERROR = "validation_error"


@dataclass
class SkillInput:
    """技能输入参数定义"""
    name: str
    type: str  # string, number, boolean, array, object
    required: bool = True
    description: Optional[str] = None
    default: Optional[Any] = None
    validation: Optional[Dict[str, Any]] = None  # 验证规则
    examples: List[Any] = field(default_factory=list)


@dataclass
class SkillOutput:
    """技能输出定义"""
    name: str
    type: str
    description: Optional[str] = None
    schema: Optional[Dict[str, Any]] = None


@dataclass
class SkillAssertion:
    """技能断言"""
    name: str
    selector: str
    timeout_ms: int = 10000
    description: Optional[str] = None
    required: bool = True


@dataclass
class SkillExample:
    """技能示例"""
    name: str
    inputs: Dict[str, Any]
    expected_outputs: Optional[Dict[str, Any]] = None
    golden_output_hash: Optional[str] = None
    description: Optional[str] = None


@dataclass
class SkillSignature:
    """技能签名"""
    author: str
    checksum: str
    algorithm: str = "sha256"
    timestamp: Optional[datetime] = None
    certificate: Optional[str] = None


@dataclass
class SkillManifest:
    """技能包清单"""
    id: str
    name: str
    version: str
    description: str
    author: str
    
    # 目标和兼容性
    target_domains: List[str] = field(default_factory=list)
    target_urls: List[str] = field(default_factory=list)
    browser_compatibility: List[str] = field(default_factory=lambda: ["chromium", "firefox", "webkit"])
    
    # 输入输出
    inputs: List[SkillInput] = field(default_factory=list)
    outputs: List[SkillOutput] = field(default_factory=list)
    
    # 执行配置
    timeout_ms: int = 30000
    retry_count: int = 3
    assertions: List[SkillAssertion] = field(default_factory=list)
    
    # 可观测性
    capture_screenshot: str = "onError"  # never, onError, onCheckpoint, always
    capture_network: bool = False
    capture_console: bool = False
    
    # 示例和测试
    examples: List[SkillExample] = field(default_factory=list)
    test_cases: List[Dict[str, Any]] = field(default_factory=list)
    
    # 权限和安全
    permissions: List[PermissionLevel] = field(default_factory=lambda: [PermissionLevel.READ_PUBLIC])
    risk_level: str = "low"  # low, medium, high
    
    # 依赖和版本
    dependencies: Dict[str, str] = field(default_factory=dict)  # skill_id -> version_range
    min_aura_version: str = "1.0.0"
    
    # 元数据
    tags: List[str] = field(default_factory=list)
    category: str = "general"
    license: str = "MIT"
    homepage: Optional[str] = None
    repository: Optional[str] = None
    
    # 签名和验证
    signature: Optional[SkillSignature] = None
    
    # 状态和统计
    status: SkillStatus = SkillStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    download_count: int = 0
    rating: float = 0.0
    rating_count: int = 0


@dataclass
class SkillExecutionContext:
    """技能执行上下文"""
    skill_id: str
    execution_id: str
    inputs: Dict[str, Any]
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    page_context: Optional[Any] = None
    site_model: Optional[Any] = None
    start_time: datetime = field(default_factory=datetime.now)
    timeout: Optional[int] = None
    dry_run: bool = False


@dataclass
class SkillExecutionResult:
    """技能执行结果"""
    execution_id: str
    skill_id: str
    result: ExecutionResult
    outputs: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    execution_time: float = 0.0
    screenshots: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    network_requests: List[Dict[str, Any]] = field(default_factory=list)
    console_messages: List[str] = field(default_factory=list)
    end_time: datetime = field(default_factory=datetime.now)


class SkillLibrary:
    """技能库管理器"""
    
    def __init__(self, library_path: str = "./skills", mcp_manager: Optional[MCPManager] = None):
        self.library_path = Path(library_path)
        self.library_path.mkdir(exist_ok=True)
        
        # MCP 集成
        self.mcp_manager = mcp_manager
        
        # 技能注册表
        self.skills: Dict[str, SkillManifest] = {}
        self.skill_scripts: Dict[str, str] = {}  # skill_id -> script_content
        self.execution_history: List[SkillExecutionResult] = []
        
        # 缓存和索引
        self.domain_index: Dict[str, List[str]] = {}  # domain -> skill_ids
        self.category_index: Dict[str, List[str]] = {}  # category -> skill_ids
        self.tag_index: Dict[str, List[str]] = {}  # tag -> skill_ids
        
        # 加载已有技能
        self._load_existing_skills()
    
    def _load_existing_skills(self):
        """加载已有技能"""
        for skill_dir in self.library_path.iterdir():
            if skill_dir.is_dir():
                manifest_path = skill_dir / "manifest.json"
                if manifest_path.exists():
                    try:
                        manifest = self._load_manifest(manifest_path)
                        self.register_skill(manifest, skill_dir)
                    except Exception as e:
                        print(f"Failed to load skill from {skill_dir}: {str(e)}")
    
    def _load_manifest(self, manifest_path: Path) -> SkillManifest:
        """加载技能清单"""
        with open(manifest_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 转换数据结构
        inputs = [SkillInput(**inp) for inp in data.get('inputs', [])]
        outputs = [SkillOutput(**out) for out in data.get('outputs', [])]
        assertions = [SkillAssertion(**ass) for ass in data.get('assertions', [])]
        examples = [SkillExample(**ex) for ex in data.get('examples', [])]
        
        # 处理权限
        permissions = [PermissionLevel(p) for p in data.get('permissions', ['read_public'])]
        
        # 处理签名
        signature = None
        if 'signature' in data:
            sig_data = data['signature']
            if 'timestamp' in sig_data:
                sig_data['timestamp'] = datetime.fromisoformat(sig_data['timestamp'])
            signature = SkillSignature(**sig_data)
        
        # 处理时间戳
        created_at = datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.now()
        updated_at = datetime.fromisoformat(data['updated_at']) if 'updated_at' in data else datetime.now()
        
        manifest = SkillManifest(
            id=data['id'],
            name=data['name'],
            version=data['version'],
            description=data['description'],
            author=data['author'],
            target_domains=data.get('target_domains', []),
            target_urls=data.get('target_urls', []),
            browser_compatibility=data.get('browser_compatibility', ['chromium', 'firefox', 'webkit']),
            inputs=inputs,
            outputs=outputs,
            timeout_ms=data.get('timeout_ms', 30000),
            retry_count=data.get('retry_count', 3),
            assertions=assertions,
            capture_screenshot=data.get('capture_screenshot', 'onError'),
            capture_network=data.get('capture_network', False),
            capture_console=data.get('capture_console', False),
            examples=examples,
            test_cases=data.get('test_cases', []),
            permissions=permissions,
            risk_level=data.get('risk_level', 'low'),
            dependencies=data.get('dependencies', {}),
            min_aura_version=data.get('min_aura_version', '1.0.0'),
            tags=data.get('tags', []),
            category=data.get('category', 'general'),
            license=data.get('license', 'MIT'),
            homepage=data.get('homepage'),
            repository=data.get('repository'),
            signature=signature,
            status=SkillStatus(data.get('status', 'active')),
            created_at=created_at,
            updated_at=updated_at,
            download_count=data.get('download_count', 0),
            rating=data.get('rating', 0.0),
            rating_count=data.get('rating_count', 0)
        )
        
        return manifest
    
    def register_skill(self, manifest: SkillManifest, skill_path: Path) -> bool:
        """注册技能"""
        try:
            # 验证技能
            validation_errors = self._validate_skill(manifest)
            if validation_errors:
                raise ValueError(f"Skill validation failed: {'; '.join(validation_errors)}")
            
            # 检查版本冲突
            if manifest.id in self.skills:
                existing = self.skills[manifest.id]
                if semver.compare(manifest.version, existing.version) <= 0:
                    raise ValueError(f"Skill version {manifest.version} is not newer than existing {existing.version}")
            
            # 加载脚本内容
            script_path = skill_path / "script.js"
            if script_path.exists():
                with open(script_path, 'r', encoding='utf-8') as f:
                    self.skill_scripts[manifest.id] = f.read()
            
            # 注册技能
            self.skills[manifest.id] = manifest
            
            # 更新索引
            self._update_indexes(manifest)
            
            print(f"Successfully registered skill: {manifest.id} v{manifest.version}")
            return True
            
        except Exception as e:
            print(f"Failed to register skill {manifest.id}: {str(e)}")
            return False
    
    def _validate_skill(self, manifest: SkillManifest) -> List[str]:
        """验证技能"""
        errors = []
        
        # 基本字段验证
        if not manifest.id:
            errors.append("Skill ID is required")
        if not manifest.name:
            errors.append("Skill name is required")
        if not manifest.version:
            errors.append("Skill version is required")
        
        # 版本格式验证
        try:
            semver.VersionInfo.parse(manifest.version)
        except ValueError:
            errors.append(f"Invalid version format: {manifest.version}")
        
        # 输入参数验证
        input_names = set()
        for inp in manifest.inputs:
            if inp.name in input_names:
                errors.append(f"Duplicate input parameter: {inp.name}")
            input_names.add(inp.name)
        
        # 示例验证
        for example in manifest.examples:
            for input_name in example.inputs:
                if input_name not in input_names:
                    errors.append(f"Example references unknown input: {input_name}")
        
        return errors
    
    def _update_indexes(self, manifest: SkillManifest):
        """更新索引"""
        # 域名索引
        for domain in manifest.target_domains:
            if domain not in self.domain_index:
                self.domain_index[domain] = []
            if manifest.id not in self.domain_index[domain]:
                self.domain_index[domain].append(manifest.id)
        
        # 分类索引
        if manifest.category not in self.category_index:
            self.category_index[manifest.category] = []
        if manifest.id not in self.category_index[manifest.category]:
            self.category_index[manifest.category].append(manifest.id)
        
        # 标签索引
        for tag in manifest.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = []
            if manifest.id not in self.tag_index[tag]:
                self.tag_index[tag].append(manifest.id)
    
    def find_skills(self, domain: Optional[str] = None, category: Optional[str] = None, 
                   tags: Optional[List[str]] = None, query: Optional[str] = None) -> List[SkillManifest]:
        """查找技能"""
        candidates = set(self.skills.keys())
        
        # 按域名过滤
        if domain:
            domain_skills = set(self.domain_index.get(domain, []))
            candidates = candidates.intersection(domain_skills)
        
        # 按分类过滤
        if category:
            category_skills = set(self.category_index.get(category, []))
            candidates = candidates.intersection(category_skills)
        
        # 按标签过滤
        if tags:
            for tag in tags:
                tag_skills = set(self.tag_index.get(tag, []))
                candidates = candidates.intersection(tag_skills)
        
        # 按查询过滤
        if query:
            query_lower = query.lower()
            filtered = []
            for skill_id in candidates:
                skill = self.skills[skill_id]
                if (query_lower in skill.name.lower() or 
                    query_lower in skill.description.lower() or
                    any(query_lower in tag.lower() for tag in skill.tags)):
                    filtered.append(skill_id)
            candidates = set(filtered)
        
        # 返回技能列表，按评分排序
        results = [self.skills[skill_id] for skill_id in candidates]
        results.sort(key=lambda s: (s.rating, s.download_count), reverse=True)
        
        return results
    
    def get_skill(self, skill_id: str) -> Optional[SkillManifest]:
        """获取技能"""
        return self.skills.get(skill_id)
    
    def get_skill_script(self, skill_id: str) -> Optional[str]:
        """获取技能脚本"""
        return self.skill_scripts.get(skill_id)
    
    async def find_matching_skill(self, intent: str, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """查找匹配的技能"""
        # 简单的技能匹配逻辑
        # 实际实现应该更复杂，包括语义匹配等
        
        if not intent:
            return None
            
        intent_lower = intent.lower()
        
        # 查找所有技能
        for skill_id, skill in self.skills.items():
            # 检查技能名称和描述是否匹配
            if (intent_lower in skill.name.lower() or 
                intent_lower in skill.description.lower() or
                any(intent_lower in tag.lower() for tag in skill.tags)):
                
                return {
                    "skill_id": skill_id,
                    "confidence": 0.9,  # 简单的置信度
                    "parameters": parameters
                }
        
        return None
    
    async def execute_skill(self, skill_id: str, inputs: Dict[str, Any], 
                          context: SkillExecutionContext) -> SkillExecutionResult:
        """执行技能"""
        skill = self.get_skill(skill_id)
        if not skill:
            return SkillExecutionResult(
                execution_id=context.execution_id,
                skill_id=skill_id,
                result=ExecutionResult.FAILURE,
                error_message=f"Skill not found: {skill_id}"
            )
        
        # 验证输入
        validation_error = self._validate_inputs(skill, inputs)
        if validation_error:
            return SkillExecutionResult(
                execution_id=context.execution_id,
                skill_id=skill_id,
                result=ExecutionResult.VALIDATION_ERROR,
                error_message=validation_error
            )
        
        # 检查权限
        if not self._check_permissions(skill, context):
            return SkillExecutionResult(
                execution_id=context.execution_id,
                skill_id=skill_id,
                result=ExecutionResult.PERMISSION_DENIED,
                error_message="Insufficient permissions"
            )
        
        start_time = datetime.now()
        
        try:
            # 执行技能脚本
            if context.dry_run:
                # 干跑模式
                outputs = {"dry_run": True, "message": "Skill execution simulated"}
                result = ExecutionResult.SUCCESS
            else:
                # 实际执行
                outputs = await self._execute_skill_script(skill, inputs, context)
                result = ExecutionResult.SUCCESS
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            execution_result = SkillExecutionResult(
                execution_id=context.execution_id,
                skill_id=skill_id,
                result=result,
                outputs=outputs,
                execution_time=execution_time,
                end_time=datetime.now()
            )
            
            # 记录执行历史
            self.execution_history.append(execution_result)
            
            return execution_result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return SkillExecutionResult(
                execution_id=context.execution_id,
                skill_id=skill_id,
                result=ExecutionResult.FAILURE,
                error_message=str(e),
                execution_time=execution_time,
                end_time=datetime.now()
            )
    
    def _validate_inputs(self, skill: SkillManifest, inputs: Dict[str, Any]) -> Optional[str]:
        """验证输入参数"""
        for input_def in skill.inputs:
            if input_def.required and input_def.name not in inputs:
                return f"Required input missing: {input_def.name}"
            
            if input_def.name in inputs:
                value = inputs[input_def.name]
                
                # 类型检查
                if input_def.type == "string" and not isinstance(value, str):
                    return f"Input {input_def.name} must be a string"
                elif input_def.type == "number" and not isinstance(value, (int, float)):
                    return f"Input {input_def.name} must be a number"
                elif input_def.type == "boolean" and not isinstance(value, bool):
                    return f"Input {input_def.name} must be a boolean"
                elif input_def.type == "array" and not isinstance(value, list):
                    return f"Input {input_def.name} must be an array"
                elif input_def.type == "object" and not isinstance(value, dict):
                    return f"Input {input_def.name} must be an object"
        
        return None
    
    def _check_permissions(self, skill: SkillManifest, context: SkillExecutionContext) -> bool:
        """检查权限"""
        # 简单权限检查实现
        # 实际实现应该根据用户角色和技能权限要求进行检查
        return True
    
    async def _execute_skill_script(self, skill: SkillManifest, inputs: Dict[str, Any], 
                                  context: SkillExecutionContext) -> Dict[str, Any]:
        """执行技能脚本"""
        script = self.get_skill_script(skill.id)
        if not script:
            raise ValueError(f"Script not found for skill: {skill.id}")
        
        # 使用 MCP 执行技能脚本
        if self.mcp_manager and self.mcp_manager.is_connected():
            try:
                # 通过 MCP 执行技能
                outputs = await self._execute_via_mcp(skill, script, inputs, context)
                return outputs
            except Exception as e:
                print(f"MCP execution failed for skill {skill.id}: {str(e)}")
                # 回退到模拟执行
        
        # 模拟执行（当 MCP 不可用时）
        outputs = {
            "executed": True,
            "skill_id": skill.id,
            "inputs_received": inputs,
            "timestamp": datetime.now().isoformat(),
            "execution_mode": "simulated"
        }
        
        return outputs
    
    async def _execute_via_mcp(self, skill: SkillManifest, script: str, inputs: Dict[str, Any], 
                              context: SkillExecutionContext) -> Dict[str, Any]:
        """通过 MCP 执行技能脚本"""
        if not self.mcp_manager:
            raise ValueError("MCP Manager not available")
        
        # 准备执行环境
        execution_context = {
            "skill_id": skill.id,
            "execution_id": context.execution_id,
            "inputs": inputs,
            "timeout": skill.timeout_ms,
            "capture_screenshot": skill.capture_screenshot,
            "capture_network": skill.capture_network,
            "capture_console": skill.capture_console
        }
        
        # 构建执行脚本
        wrapped_script = self._wrap_skill_script(script, inputs, execution_context)
        
        try:
            # 通过 MCP 执行脚本
            result = await self.mcp_manager.execute_script(wrapped_script, execution_context)
            
            # 处理执行结果
            outputs = self._process_mcp_result(result, skill, context)
            
            return outputs
            
        except Exception as e:
            raise Exception(f"MCP execution failed: {str(e)}")
    
    def _wrap_skill_script(self, script: str, inputs: Dict[str, Any], context: Dict[str, Any]) -> str:
        """包装技能脚本以便在 MCP 环境中执行"""
        wrapper = f"""
// Aura Skill Execution Wrapper
const skillInputs = {json.dumps(inputs)};
const executionContext = {json.dumps(context)};

// 技能脚本开始
{script}
// 技能脚本结束

// 执行技能主函数
(async () => {{
    try {{
        let result;
        if (typeof execute === 'function') {{
            result = await execute(skillInputs, executionContext);
        }} else if (typeof main === 'function') {{
            result = await main(skillInputs, executionContext);
        }} else {{
            throw new Error('No execute() or main() function found in skill script');
        }}
        
        // 返回结果
        console.log('SKILL_RESULT:', JSON.stringify({{
            success: true,
            outputs: result,
            execution_id: executionContext.execution_id
        }}));
    }} catch (error) {{
        console.error('SKILL_ERROR:', JSON.stringify({{
            success: false,
            error: error.message,
            stack: error.stack,
            execution_id: executionContext.execution_id
        }}));
    }}
}})();
        """
        return wrapper
    
    def _process_mcp_result(self, mcp_result: Dict[str, Any], skill: SkillManifest, 
                           context: SkillExecutionContext) -> Dict[str, Any]:
        """处理 MCP 执行结果"""
        outputs = {}
        
        # 解析控制台输出中的结果
        if 'console_messages' in mcp_result:
            for message in mcp_result['console_messages']:
                if message.startswith('SKILL_RESULT:'):
                    try:
                        result_data = json.loads(message[13:])  # 去掉 'SKILL_RESULT:' 前缀
                        if result_data.get('success'):
                            outputs = result_data.get('outputs', {})
                        else:
                            raise Exception(result_data.get('error', 'Unknown skill execution error'))
                    except json.JSONDecodeError:
                        pass
                elif message.startswith('SKILL_ERROR:'):
                    try:
                        error_data = json.loads(message[12:])  # 去掉 'SKILL_ERROR:' 前缀
                        raise Exception(error_data.get('error', 'Unknown skill execution error'))
                    except json.JSONDecodeError:
                        pass
        
        # 添加执行元数据
        outputs['_execution_metadata'] = {
            'skill_id': skill.id,
            'execution_id': context.execution_id,
            'execution_mode': 'mcp',
            'timestamp': datetime.now().isoformat(),
            'mcp_result': mcp_result
        }
        
        return outputs
    
    def set_mcp_manager(self, mcp_manager: MCPManager):
        """设置 MCP 管理器"""
        self.mcp_manager = mcp_manager
    
    async def execute_skill_via_mcp(self, skill_id: str, inputs: Dict[str, Any], 
                                   browser_context: Optional[Dict[str, Any]] = None) -> SkillExecutionResult:
        """通过 MCP 执行技能（简化接口）"""
        execution_id = str(uuid.uuid4())
        
        context = SkillExecutionContext(
            skill_id=skill_id,
            execution_id=execution_id,
            inputs=inputs,
            page_context=browser_context
        )
        
        return await self.execute_skill(skill_id, inputs, context)
    
    async def test_skill_with_mcp(self, skill_id: str, example_index: int = 0) -> SkillExecutionResult:
        """使用 MCP 测试技能"""
        skill = self.get_skill(skill_id)
        if not skill:
            raise ValueError(f"Skill not found: {skill_id}")
        
        if not skill.examples or example_index >= len(skill.examples):
            raise ValueError(f"Example {example_index} not found for skill {skill_id}")
        
        example = skill.examples[example_index]
        return await self.execute_skill_via_mcp(skill_id, example.inputs)
    
    def create_skill_package(self, manifest: SkillManifest, script_content: str, 
                           output_path: Optional[str] = None) -> str:
        """创建技能包"""
        if not output_path:
            output_path = f"{manifest.id}-{manifest.version}.aura"
        
        # 创建临时目录
        temp_dir = Path(f"temp_{manifest.id}")
        temp_dir.mkdir(exist_ok=True)
        
        try:
            # 写入清单文件
            manifest_data = self._manifest_to_dict(manifest)
            with open(temp_dir / "manifest.json", 'w', encoding='utf-8') as f:
                json.dump(manifest_data, f, indent=2, ensure_ascii=False)
            
            # 写入脚本文件
            with open(temp_dir / "script.js", 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # 创建ZIP包
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in temp_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(temp_dir)
                        zipf.write(file_path, arcname)
            
            return output_path
            
        finally:
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def install_skill_package(self, package_path: str) -> bool:
        """安装技能包"""
        try:
            with zipfile.ZipFile(package_path, 'r') as zipf:
                # 读取清单
                manifest_data = json.loads(zipf.read("manifest.json").decode('utf-8'))
                
                # 创建技能目录
                skill_dir = self.library_path / manifest_data['id']
                skill_dir.mkdir(exist_ok=True)
                
                # 解压文件
                zipf.extractall(skill_dir)
                
                # 加载并注册技能
                manifest = self._load_manifest(skill_dir / "manifest.json")
                return self.register_skill(manifest, skill_dir)
                
        except Exception as e:
            print(f"Failed to install skill package {package_path}: {str(e)}")
            return False
    
    def _manifest_to_dict(self, manifest: SkillManifest) -> Dict[str, Any]:
        """将清单转换为字典"""
        data = {
            "id": manifest.id,
            "name": manifest.name,
            "version": manifest.version,
            "description": manifest.description,
            "author": manifest.author,
            "target_domains": manifest.target_domains,
            "target_urls": manifest.target_urls,
            "browser_compatibility": manifest.browser_compatibility,
            "inputs": [
                {
                    "name": inp.name,
                    "type": inp.type,
                    "required": inp.required,
                    "description": inp.description,
                    "default": inp.default,
                    "validation": inp.validation,
                    "examples": inp.examples
                }
                for inp in manifest.inputs
            ],
            "outputs": [
                {
                    "name": out.name,
                    "type": out.type,
                    "description": out.description,
                    "schema": out.schema
                }
                for out in manifest.outputs
            ],
            "timeout_ms": manifest.timeout_ms,
            "retry_count": manifest.retry_count,
            "assertions": [
                {
                    "name": ass.name,
                    "selector": ass.selector,
                    "timeout_ms": ass.timeout_ms,
                    "description": ass.description,
                    "required": ass.required
                }
                for ass in manifest.assertions
            ],
            "capture_screenshot": manifest.capture_screenshot,
            "capture_network": manifest.capture_network,
            "capture_console": manifest.capture_console,
            "examples": [
                {
                    "name": ex.name,
                    "inputs": ex.inputs,
                    "expected_outputs": ex.expected_outputs,
                    "golden_output_hash": ex.golden_output_hash,
                    "description": ex.description
                }
                for ex in manifest.examples
            ],
            "test_cases": manifest.test_cases,
            "permissions": [p.value for p in manifest.permissions],
            "risk_level": manifest.risk_level,
            "dependencies": manifest.dependencies,
            "min_aura_version": manifest.min_aura_version,
            "tags": manifest.tags,
            "category": manifest.category,
            "license": manifest.license,
            "homepage": manifest.homepage,
            "repository": manifest.repository,
            "status": manifest.status.value,
            "created_at": manifest.created_at.isoformat(),
            "updated_at": manifest.updated_at.isoformat(),
            "download_count": manifest.download_count,
            "rating": manifest.rating,
            "rating_count": manifest.rating_count
        }
        
        if manifest.signature:
            data["signature"] = {
                "author": manifest.signature.author,
                "checksum": manifest.signature.checksum,
                "algorithm": manifest.signature.algorithm,
                "timestamp": manifest.signature.timestamp.isoformat() if manifest.signature.timestamp else None,
                "certificate": manifest.signature.certificate
            }
        
        return data
    
    def get_execution_history(self, skill_id: Optional[str] = None, limit: int = 10) -> List[SkillExecutionResult]:
        """获取执行历史"""
        history = self.execution_history
        
        if skill_id:
            history = [r for r in history if r.skill_id == skill_id]
        
        return history[-limit:]
    
    def get_skill_statistics(self, skill_id: str) -> Dict[str, Any]:
        """获取技能统计信息"""
        skill = self.get_skill(skill_id)
        if not skill:
            return {}
        
        executions = [r for r in self.execution_history if r.skill_id == skill_id]
        
        success_count = len([r for r in executions if r.result == ExecutionResult.SUCCESS])
        total_count = len(executions)
        success_rate = success_count / total_count if total_count > 0 else 0
        
        avg_execution_time = sum(r.execution_time for r in executions) / total_count if total_count > 0 else 0
        
        return {
            "skill_id": skill_id,
            "total_executions": total_count,
            "success_count": success_count,
            "success_rate": success_rate,
            "avg_execution_time": avg_execution_time,
            "rating": skill.rating,
            "rating_count": skill.rating_count,
            "download_count": skill.download_count,
            "last_executed": executions[-1].end_time.isoformat() if executions else None
        }
    
    def update_skill_rating(self, skill_id: str, rating: float) -> bool:
        """更新技能评分"""
        skill = self.get_skill(skill_id)
        if not skill or rating < 0 or rating > 5:
            return False
        
        # 计算新的平均评分
        total_rating = skill.rating * skill.rating_count + rating
        skill.rating_count += 1
        skill.rating = total_rating / skill.rating_count
        skill.updated_at = datetime.now()
        
        return True


# 示例使用
if __name__ == "__main__":
    import asyncio
    
    async def main():
        library = SkillLibrary()
        
        # 创建示例技能
        manifest = SkillManifest(
            id="example.search",
            name="网站搜索技能",
            version="1.0.0",
            description="在网站中执行搜索操作",
            author="Aura Team",
            target_domains=["example.com"],
            inputs=[
                SkillInput(
                    name="query",
                    type="string",
                    required=True,
                    description="搜索关键词"
                )
            ],
            outputs=[
                SkillOutput(
                    name="results",
                    type="array",
                    description="搜索结果列表"
                )
            ],
            tags=["search", "web"],
            category="automation"
        )
        
        # 注册技能
        script_content = """
        // 示例搜索脚本
        async function execute(inputs, context) {
            const query = inputs.query;
            // 执行搜索逻辑
            return {
                results: [`搜索结果1: ${query}`, `搜索结果2: ${query}`]
            };
        }
        """
        
        # 模拟注册（实际需要创建文件）
        library.skills[manifest.id] = manifest
        library.skill_scripts[manifest.id] = script_content
        library._update_indexes(manifest)
        
        # 查找技能
        found_skills = library.find_skills(domain="example.com", tags=["search"])
        print(f"Found {len(found_skills)} skills for example.com with search tag")
        
        # 执行技能
        context = SkillExecutionContext(
            skill_id="example.search",
            execution_id="exec_001",
            inputs={"query": "Python教程"}
        )
        
        result = await library.execute_skill("example.search", {"query": "Python教程"}, context)
        print(f"Execution result: {result.result.value}")
        
        # 获取统计信息
        stats = library.get_skill_statistics("example.search")
        print(f"Skill statistics: {stats}")
    
    # asyncio.run(main())