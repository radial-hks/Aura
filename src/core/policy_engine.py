"""Policy Engine - 策略引擎

负责系统的安全策略检查、权限控制和合规性验证。
确保所有操作符合安全规范和用户权限。
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
        self.rules: List[PolicyRule] = []
        self.user_permissions: Dict[str, List[PermissionLevel]] = {}
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
        """检查策略
        
        Args:
            parsed_command: 解析后的命令
            risk_assessment: 风险评估结果
            
        Returns:
            策略检查结果
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
        """请求人工审批
        
        Args:
            task_id: 任务ID
            reason: 审批原因
            
        Returns:
            是否批准
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
        """获取策略统计信息
        
        Returns:
            统计信息
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