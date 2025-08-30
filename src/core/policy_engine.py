"""策略引擎模块 - Policy Engine

本模块是Aura系统的安全控制核心，负责管理和执行安全策略，确保所有自动化操作
都在安全可控的范围内进行。

核心职责：
1. 策略规则管理：定义、存储和维护各种安全策略规则
2. 权限控制：基于用户身份和操作类型进行权限验证
3. 风险评估集成：结合风险引擎的评估结果做出策略决策
4. 审批流程：对高风险操作启动人工审批机制
5. 多因子认证：对敏感操作要求额外的身份验证

架构设计：
- 基于规则的策略引擎，支持优先级和条件匹配
- 可扩展的策略动作类型（允许、拒绝、需要审批、需要MFA）
- 灵活的条件匹配系统（URL模式、域名、操作类型、风险级别等）
- 用户权限分级管理

使用示例：
    engine = PolicyEngine()
    result = await engine.check_policy(parsed_command, risk_assessment)
    if result.approval_required:
        approved = await engine.request_approval(task_id, result.reason)

注意事项：
- 默认采用拒绝策略，只有明确允许的操作才会被执行
- 策略规则按优先级排序，优先级低的规则优先匹配
- 支持动态添加、删除和更新策略规则
- 审批流程需要与外部系统集成（如企业IM、邮件等）
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from ..utils.logger import get_logger
from ..utils.exceptions import PolicyViolationError

logger = get_logger(__name__)


class PolicyAction(Enum):
    """策略动作枚举"""
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    REQUIRE_MFA = "require_mfa"


class PermissionLevel(Enum):
    """权限级别枚举"""
    READ_ONLY = "read_only"
    READ_PUBLIC = "read_public"
    WRITE_SAFE = "write_safe"
    WRITE_SENSITIVE = "write_sensitive"
    ADMIN = "admin"


@dataclass
class PolicyRule:
    """策略规则数据结构"""
    id: str
    name: str
    description: str
    conditions: Dict[str, Any]
    action: PolicyAction
    priority: int = 100
    enabled: bool = True


@dataclass
class PolicyCheckResult:
    """策略检查结果"""
    allowed: bool
    action: PolicyAction
    reason: Optional[str] = None
    required_permissions: List[PermissionLevel] = None
    approval_required: bool = False
    mfa_required: bool = False


class PolicyEngine:
    """策略引擎
    
    实现安全策略检查和权限控制：
    1. 定义和管理安全策略规则
    2. 检查操作是否符合策略
    3. 处理权限验证
    4. 记录策略违规事件
    """
    
    def __init__(self):
        """初始化策略引擎
        
        创建策略引擎实例，初始化规则存储和用户权限管理系统。
        自动加载默认的安全策略规则。
        
        初始化内容：
        - 策略规则列表：存储所有策略规则
        - 用户权限映射：管理用户ID到权限级别的映射
        - 默认规则加载：加载系统预定义的安全策略
        
        设计考虑：
        - 规则列表支持动态修改，便于运行时策略调整
        - 用户权限采用字典存储，支持快速查找
        - 默认规则确保系统启动后即具备基本安全保护
        """
        # 策略规则存储 - 按优先级排序执行
        self.rules: List[PolicyRule] = []
        
        # 用户权限管理 - 用户ID到权限级别的映射
        self.user_permissions: Dict[str, List[PermissionLevel]] = {}
        
        # 加载系统默认安全策略
        self._load_default_rules()
        
        logger.info("PolicyEngine initialized")
    
    def _load_default_rules(self):
        """加载默认策略规则"""
        default_rules = [
            PolicyRule(
                id="deny_sensitive_data",
                name="禁止访问敏感数据",
                description="禁止访问包含密码、信用卡等敏感信息的页面",
                conditions={
                    "url_patterns": ["*/login", "*/password", "*/payment", "*/credit-card"],
                    "element_types": ["password", "credit-card-number"]
                },
                action=PolicyAction.DENY,
                priority=10
            ),
            PolicyRule(
                id="require_approval_financial",
                name="金融操作需要审批",
                description="涉及金融交易的操作需要人工审批",
                conditions={
                    "domains": ["bank.com", "paypal.com", "alipay.com"],
                    "actions": ["transfer", "payment", "purchase"]
                },
                action=PolicyAction.REQUIRE_APPROVAL,
                priority=20
            ),
            PolicyRule(
                id="limit_form_submission",
                name="限制表单提交",
                description="限制向外部网站提交表单",
                conditions={
                    "action_types": ["form_submit"],
                    "external_domains": True
                },
                action=PolicyAction.REQUIRE_APPROVAL,
                priority=30
            ),
            PolicyRule(
                id="allow_read_only",
                name="允许只读操作",
                description="允许所有只读操作",
                conditions={
                    "action_types": ["navigate", "read", "extract", "screenshot", "search"]
                },
                action=PolicyAction.ALLOW,
                priority=100
            )
        ]
        
        self.rules.extend(default_rules)
        logger.info(f"Loaded {len(default_rules)} default policy rules")
    
    async def check_policy(self, parsed_command: Dict[str, Any], 
                          risk_assessment: Dict[str, Any]) -> PolicyCheckResult:
        """执行策略检查 - 系统安全控制的核心方法
        
        根据解析后的命令和风险评估结果，遍历所有启用的策略规则，
        找到第一个匹配的规则并返回相应的策略决策。
        
        Args:
            parsed_command: 解析后的命令对象，包含：
                - primary_intent: 主要意图（如导航、点击、输入等）
                - context: 上下文信息（目标URL、域名、元素类型等）
                - parameters: 命令参数
            risk_assessment: 风险引擎的评估结果，包含：
                - level: 风险级别（low/medium/high/critical）
                - factors: 风险因子列表
                - score: 风险评分
                - recommendations: 建议措施
            
        Returns:
            PolicyCheckResult: 策略检查结果，包含：
                - allowed: 是否允许执行
                - action: 策略动作（允许/拒绝/需要审批/需要MFA）
                - reason: 决策原因
                - approval_required: 是否需要人工审批
                - mfa_required: 是否需要多因子认证
        
        执行流程：
        1. 按优先级排序所有启用的策略规则
        2. 逐一检查规则条件是否匹配当前命令和风险评估
        3. 返回第一个匹配规则的策略动作
        4. 如无匹配规则，默认拒绝执行
        
        性能考虑：
        - 规则按优先级预排序，避免每次检查时排序
        - 短路评估，找到匹配规则即返回
        - 异步设计，支持复杂条件的异步验证
        """
        logger.debug(f"Checking policy for command: {getattr(parsed_command.primary_intent, 'intent', 'unknown').value if hasattr(parsed_command, 'primary_intent') and parsed_command.primary_intent and hasattr(getattr(parsed_command.primary_intent, 'intent', ''), 'value') else 'unknown'}")
        
        # 按优先级排序规则
        sorted_rules = sorted(self.rules, key=lambda r: r.priority)
        
        for rule in sorted_rules:
            if not rule.enabled:
                continue
            
            if await self._match_rule(rule, parsed_command, risk_assessment):
                logger.info(f"Policy rule matched: {rule.name}")
                
                if rule.action == PolicyAction.DENY:
                    return PolicyCheckResult(
                        allowed=False,
                        action=rule.action,
                        reason=f"Denied by policy rule: {rule.name}"
                    )
                elif rule.action == PolicyAction.REQUIRE_APPROVAL:
                    return PolicyCheckResult(
                        allowed=True,
                        action=rule.action,
                        reason=f"Approval required by policy rule: {rule.name}",
                        approval_required=True
                    )
                elif rule.action == PolicyAction.REQUIRE_MFA:
                    return PolicyCheckResult(
                        allowed=True,
                        action=rule.action,
                        reason=f"MFA required by policy rule: {rule.name}",
                        mfa_required=True
                    )
                elif rule.action == PolicyAction.ALLOW:
                    return PolicyCheckResult(
                        allowed=True,
                        action=rule.action,
                        reason=f"Allowed by policy rule: {rule.name}"
                    )
        
        # 默认拒绝
        return PolicyCheckResult(
            allowed=False,
            action=PolicyAction.DENY,
            reason="No matching policy rule found, default deny"
        )
    
    async def _match_rule(self, rule: PolicyRule, parsed_command: Dict[str, Any], 
                         risk_assessment: Dict[str, Any]) -> bool:
        """检查规则是否匹配
        
        Args:
            rule: 策略规则
            parsed_command: 解析后的命令
            risk_assessment: 风险评估结果
            
        Returns:
            是否匹配
        """
        conditions = rule.conditions
        
        # 检查URL模式
        if "url_patterns" in conditions:
            target_url = getattr(parsed_command, 'context', {}).get('target_url', '')
            for pattern in conditions["url_patterns"]:
                if self._match_pattern(pattern, target_url):
                    return True
        
        # 检查域名
        if "domains" in conditions:
            target_domain = getattr(parsed_command, 'context', {}).get('target_domain', '')
            if target_domain in conditions["domains"]:
                return True
        
        # 检查操作类型
        if "action_types" in conditions:
            # 处理ParsedCommand对象
            if hasattr(parsed_command, 'primary_intent') and parsed_command.primary_intent:
                intent_type = parsed_command.primary_intent.intent.value.lower()
                if intent_type in conditions["action_types"]:
                    return True
            # 处理字典格式
            elif isinstance(parsed_command, dict):
                action_type = parsed_command.get("action_type", "").lower() if isinstance(parsed_command.get("action_type", ""), str) else ""
                if action_type in conditions["action_types"]:
                    return True
        
        # 检查元素类型
        if "element_types" in conditions:
            element_types = getattr(parsed_command, 'context', {}).get('element_types', [])
            for elem_type in element_types:
                if elem_type in conditions["element_types"]:
                    return True
        
        # 检查风险级别
        if "min_risk_level" in conditions:
            risk_level = risk_assessment.get("level", "low")
            min_risk = conditions["min_risk_level"]
            risk_levels = ["low", "medium", "high", "critical"]
            if risk_levels.index(risk_level) >= risk_levels.index(min_risk):
                return True
        
        # 检查外部域名
        if "external_domains" in conditions and conditions["external_domains"]:
            is_external = getattr(parsed_command, 'context', {}).get('is_external_domain', False)
            if is_external:
                return True
        
        return False
    
    def _match_pattern(self, pattern: str, text: str) -> bool:
        """匹配模式
        
        Args:
            pattern: 模式字符串（支持*通配符）
            text: 待匹配文本
            
        Returns:
            是否匹配
        """
        import re
        # 将*转换为正则表达式
        regex_pattern = pattern.replace("*", ".*")
        return bool(re.match(regex_pattern, text, re.IGNORECASE))
    
    def add_rule(self, rule: PolicyRule):
        """添加策略规则
        
        Args:
            rule: 策略规则
        """
        self.rules.append(rule)
        logger.info(f"Added policy rule: {rule.name}")
    
    def remove_rule(self, rule_id: str) -> bool:
        """移除策略规则
        
        Args:
            rule_id: 规则ID
            
        Returns:
            是否成功移除
        """
        for i, rule in enumerate(self.rules):
            if rule.id == rule_id:
                del self.rules[i]
                logger.info(f"Removed policy rule: {rule_id}")
                return True
        return False
    
    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """更新策略规则
        
        Args:
            rule_id: 规则ID
            updates: 更新内容
            
        Returns:
            是否成功更新
        """
        for rule in self.rules:
            if rule.id == rule_id:
                for key, value in updates.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                logger.info(f"Updated policy rule: {rule_id}")
                return True
        return False
    
    def get_rules(self) -> List[PolicyRule]:
        """获取所有策略规则
        
        Returns:
            策略规则列表
        """
        return self.rules.copy()
    
    def set_user_permissions(self, user_id: str, permissions: List[PermissionLevel]):
        """设置用户权限
        
        Args:
            user_id: 用户ID
            permissions: 权限列表
        """
        self.user_permissions[user_id] = permissions
        logger.info(f"Set permissions for user {user_id}: {[p.value for p in permissions]}")
    
    def check_user_permission(self, user_id: str, required_permission: PermissionLevel) -> bool:
        """检查用户权限
        
        Args:
            user_id: 用户ID
            required_permission: 所需权限
            
        Returns:
            是否有权限
        """
        user_perms = self.user_permissions.get(user_id, [])
        return required_permission in user_perms
    
    async def request_approval(self, task_id: str, reason: str) -> bool:
        """请求人工审批 - 高风险操作的安全保障机制
        
        当策略引擎判定某个操作需要人工审批时，通过此方法启动审批流程。
        支持多种审批渠道和超时控制。
        
        Args:
            task_id: 任务唯一标识符，用于跟踪审批状态
            reason: 需要审批的具体原因，向审批者说明风险点
            
        Returns:
            bool: 审批结果
                - True: 审批通过，可以执行操作
                - False: 审批拒绝，禁止执行操作
        
        实现考虑：
        - 支持多种通知渠道（邮件、IM、短信等）
        - 设置合理的审批超时时间
        - 记录完整的审批日志用于审计
        - 支持审批权限分级（不同风险级别需要不同级别审批者）
        
        集成要求：
        - 需要与企业通知系统集成
        - 需要与用户管理系统集成获取审批者信息
        - 需要与审计系统集成记录审批历史
        
        当前实现：
        - 简化版本，直接返回True用于演示
        - 生产环境需要替换为真实的审批流程
        """
        logger.info(f"Approval requested for task {task_id}: {reason}")
        
        # 这里应该实现实际的审批流程
        # 例如发送通知、等待审批响应等
        # 简化实现，直接返回True
        
        # 模拟审批延迟
        import asyncio
        await asyncio.sleep(1)
        
        # 在实际实现中，这里应该等待真实的审批结果
        approved = True  # 简化实现
        
        logger.info(f"Approval result for task {task_id}: {'approved' if approved else 'denied'}")
        return approved
    
    def get_policy_stats(self) -> Dict[str, Any]:
        """获取策略引擎统计信息 - 用于监控和运维
        
        提供策略引擎的运行状态和配置统计，帮助管理员了解
        当前的策略配置情况和系统安全状态。
        
        Returns:
            Dict[str, Any]: 包含以下统计信息的字典：
                - total_rules: 策略规则总数
                - enabled_rules: 启用的策略规则数量
                - rule_types: 按策略动作类型分组的规则数量统计
                    - allow: 允许类规则数量
                    - deny: 拒绝类规则数量  
                    - require_approval: 需要审批类规则数量
                    - require_mfa: 需要MFA类规则数量
                - total_users: 配置权限的用户总数
        
        使用场景：
        - 系统监控面板展示策略配置状态
        - 安全审计报告生成
        - 策略配置合理性分析
        - 运维告警阈值设置
        
        扩展建议：
        - 添加策略执行统计（通过/拒绝/审批次数）
        - 添加性能指标（平均检查耗时等）
        - 添加热点规则分析（最常匹配的规则）
        """
        return {
            "total_rules": len(self.rules),
            "enabled_rules": len([r for r in self.rules if r.enabled]),
            "rule_types": {
                action.value: len([r for r in self.rules if r.action == action])
                for action in PolicyAction
            },
            "total_users": len(self.user_permissions)
        }