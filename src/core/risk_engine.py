"""Risk Engine - 风险评估引擎

负责分析和评估操作的风险级别，为策略引擎提供决策依据。
基于多维度因素进行风险评估。
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import re
from urllib.parse import urlparse

from ..utils.logger import get_logger

logger = get_logger(__name__)


class RiskLevel(Enum):
    """风险级别枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(Enum):
    """风险类别枚举"""
    DATA_PRIVACY = "data_privacy"
    FINANCIAL = "financial"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"


@dataclass
class RiskFactor:
    """风险因子数据结构"""
    category: RiskCategory
    name: str
    description: str
    weight: float  # 权重 0.0-1.0
    threshold: float  # 阈值


@dataclass
class RiskAssessment:
    """风险评估结果"""
    level: RiskLevel
    score: float  # 风险分数 0.0-1.0
    factors: List[Dict[str, Any]]  # 触发的风险因子
    recommendations: List[str]  # 建议措施
    requires_monitoring: bool = False
    requires_approval: bool = False


class RiskEngine:
    """风险评估引擎
    
    实现多维度风险评估：
    1. 基于URL和域名的风险评估
    2. 基于操作类型的风险评估
    3. 基于数据敏感性的风险评估
    4. 基于用户行为的风险评估
    """
    
    def __init__(self):
        self.risk_factors: List[RiskFactor] = []
        self.domain_blacklist: List[str] = []
        self.sensitive_patterns: List[str] = []
        self._load_risk_factors()
        self._load_security_data()
        
        logger.info("RiskEngine initialized")
    
    def _load_risk_factors(self):
        """加载风险因子"""
        risk_factors = [
            # 数据隐私风险
            RiskFactor(
                category=RiskCategory.DATA_PRIVACY,
                name="personal_data_access",
                description="访问个人敏感数据",
                weight=0.8,
                threshold=0.3
            ),
            RiskFactor(
                category=RiskCategory.DATA_PRIVACY,
                name="form_data_submission",
                description="提交表单数据",
                weight=0.6,
                threshold=0.4
            ),
            
            # 金融风险
            RiskFactor(
                category=RiskCategory.FINANCIAL,
                name="payment_operation",
                description="涉及支付操作",
                weight=0.9,
                threshold=0.2
            ),
            RiskFactor(
                category=RiskCategory.FINANCIAL,
                name="financial_data_access",
                description="访问金融数据",
                weight=0.7,
                threshold=0.3
            ),
            
            # 安全风险
            RiskFactor(
                category=RiskCategory.SECURITY,
                name="external_domain_access",
                description="访问外部域名",
                weight=0.5,
                threshold=0.5
            ),
            RiskFactor(
                category=RiskCategory.SECURITY,
                name="file_download",
                description="文件下载操作",
                weight=0.6,
                threshold=0.4
            ),
            
            # 合规风险
            RiskFactor(
                category=RiskCategory.COMPLIANCE,
                name="data_export",
                description="数据导出操作",
                weight=0.7,
                threshold=0.3
            ),
            
            # 操作风险
            RiskFactor(
                category=RiskCategory.OPERATIONAL,
                name="bulk_operation",
                description="批量操作",
                weight=0.4,
                threshold=0.6
            ),
            RiskFactor(
                category=RiskCategory.OPERATIONAL,
                name="irreversible_action",
                description="不可逆操作",
                weight=0.8,
                threshold=0.3
            )
        ]
        
        self.risk_factors.extend(risk_factors)
        logger.info(f"Loaded {len(risk_factors)} risk factors")
    
    def _load_security_data(self):
        """加载安全数据"""
        # 域名黑名单
        self.domain_blacklist = [
            "malware-site.com",
            "phishing-example.com",
            "suspicious-domain.net"
        ]
        
        # 敏感数据模式
        self.sensitive_patterns = [
            r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",  # 信用卡号
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"password",
            r"credit[\s-]?card",
            r"social[\s-]?security",
            r"bank[\s-]?account"
        ]
        
        logger.info("Security data loaded")
    
    async def assess_risk(self, parsed_command: Dict[str, Any], 
                         base_risk_level: RiskLevel = RiskLevel.LOW) -> RiskAssessment:
        """评估风险
        
        Args:
            parsed_command: 解析后的命令
            base_risk_level: 基础风险级别
            
        Returns:
            风险评估结果
        """
        logger.debug(f"Assessing risk for command: {getattr(parsed_command.primary_intent, 'intent', 'unknown').value if hasattr(parsed_command, 'primary_intent') and parsed_command.primary_intent and hasattr(getattr(parsed_command.primary_intent, 'intent', ''), 'value') else 'unknown'}")
        
        risk_score = 0.0
        triggered_factors = []
        recommendations = []
        
        # 1. URL和域名风险评估
        url_risk = await self._assess_url_risk(parsed_command)
        risk_score += url_risk["score"]
        triggered_factors.extend(url_risk["factors"])
        
        # 2. 操作类型风险评估
        action_risk = await self._assess_action_risk(parsed_command)
        risk_score += action_risk["score"]
        triggered_factors.extend(action_risk["factors"])
        
        # 3. 数据敏感性风险评估
        data_risk = await self._assess_data_risk(parsed_command)
        risk_score += data_risk["score"]
        triggered_factors.extend(data_risk["factors"])
        
        # 4. 用户行为风险评估
        behavior_risk = await self._assess_behavior_risk(parsed_command)
        risk_score += behavior_risk["score"]
        triggered_factors.extend(behavior_risk["factors"])
        
        # 归一化风险分数
        risk_score = min(risk_score, 1.0)
        
        # 确定风险级别
        if risk_score >= 0.8:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 0.6:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 0.3:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
        
        # 生成建议
        recommendations = self._generate_recommendations(triggered_factors, risk_level)
        
        # 确定是否需要监控和审批
        requires_monitoring = risk_score >= 0.4
        requires_approval = risk_score >= 0.7
        
        assessment = RiskAssessment(
            level=risk_level,
            score=risk_score,
            factors=triggered_factors,
            recommendations=recommendations,
            requires_monitoring=requires_monitoring,
            requires_approval=requires_approval
        )
        
        logger.info(f"Risk assessment completed: level={risk_level.value}, score={risk_score:.2f}")
        return assessment
    
    async def _assess_url_risk(self, parsed_command: Dict[str, Any]) -> Dict[str, Any]:
        """评估URL风险
        
        Args:
            parsed_command: 解析后的命令
            
        Returns:
            URL风险评估结果
        """
        score = 0.0
        factors = []
        
        target_url = getattr(parsed_command, 'context', {}).get('target_url', '')
        if not target_url:
            return {"score": score, "factors": factors}
        
        try:
            parsed_url = urlparse(target_url)
            domain = parsed_url.netloc.lower()
            
            # 检查域名黑名单
            if domain in self.domain_blacklist:
                score += 0.9
                factors.append({
                    "name": "blacklisted_domain",
                    "description": f"域名在黑名单中: {domain}",
                    "severity": "critical"
                })
            
            # 检查是否为外部域名
            if self._is_external_domain(domain):
                score += 0.3
                factors.append({
                    "name": "external_domain",
                    "description": f"访问外部域名: {domain}",
                    "severity": "medium"
                })
            
            # 检查URL路径中的敏感关键词
            sensitive_keywords = ["admin", "login", "password", "payment", "checkout"]
            path = parsed_url.path.lower()
            for keyword in sensitive_keywords:
                if keyword in path:
                    score += 0.2
                    factors.append({
                        "name": "sensitive_url_path",
                        "description": f"URL路径包含敏感关键词: {keyword}",
                        "severity": "low"
                    })
                    break
            
        except Exception as e:
            logger.warning(f"Failed to parse URL {target_url}: {e}")
        
        return {"score": score, "factors": factors}
    
    async def _assess_action_risk(self, parsed_command: Dict[str, Any]) -> Dict[str, Any]:
        """评估操作风险
        
        Args:
            parsed_command: 解析后的命令
            
        Returns:
            操作风险评估结果
        """
        score = 0.0
        factors = []
        
        action_type = getattr(parsed_command.primary_intent, 'intent', '').value.lower() if hasattr(parsed_command, 'primary_intent') and parsed_command.primary_intent and hasattr(getattr(parsed_command.primary_intent, 'intent', ''), 'value') else ''
        intent = action_type
        
        # 高风险操作
        high_risk_actions = ["submit", "delete", "purchase", "transfer", "payment"]
        if action_type in high_risk_actions or any(action in intent.lower() for action in high_risk_actions):
            score += 0.7
            factors.append({
                "name": "high_risk_action",
                "description": f"执行高风险操作: {action_type or intent}",
                "severity": "high"
            })
        
        # 中风险操作
        medium_risk_actions = ["upload", "download", "modify", "update"]
        if action_type in medium_risk_actions or any(action in intent.lower() for action in medium_risk_actions):
            score += 0.4
            factors.append({
                "name": "medium_risk_action",
                "description": f"执行中风险操作: {action_type or intent}",
                "severity": "medium"
            })
        
        # 批量操作
        if "batch" in intent.lower() or "bulk" in intent.lower() or "all" in intent.lower():
            score += 0.3
            factors.append({
                "name": "bulk_operation",
                "description": "执行批量操作",
                "severity": "medium"
            })
        
        return {"score": score, "factors": factors}
    
    async def _assess_data_risk(self, parsed_command: Dict[str, Any]) -> Dict[str, Any]:
        """评估数据风险
        
        Args:
            parsed_command: 解析后的命令
            
        Returns:
            数据风险评估结果
        """
        score = 0.0
        factors = []
        
        # 检查参数中的敏感数据
        parameters = getattr(parsed_command, 'context', {})
        for key, value in parameters.items():
            if isinstance(value, str):
                for pattern in self.sensitive_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        score += 0.6
                        factors.append({
                            "name": "sensitive_data_detected",
                            "description": f"检测到敏感数据模式: {pattern}",
                            "severity": "high"
                        })
                        break
        
        # 检查是否涉及个人信息
        personal_data_keywords = ["name", "email", "phone", "address", "birthday"]
        intent = getattr(parsed_command.primary_intent, 'intent', '').value.lower() if hasattr(parsed_command, 'primary_intent') and parsed_command.primary_intent and hasattr(getattr(parsed_command.primary_intent, 'intent', ''), 'value') else ''
        for keyword in personal_data_keywords:
            if keyword in intent:
                score += 0.3
                factors.append({
                    "name": "personal_data_access",
                    "description": f"可能涉及个人信息: {keyword}",
                    "severity": "medium"
                })
        
        return {"score": score, "factors": factors}
    
    async def _assess_behavior_risk(self, parsed_command: Dict[str, Any]) -> Dict[str, Any]:
        """评估用户行为风险
        
        Args:
            parsed_command: 解析后的命令
            
        Returns:
            行为风险评估结果
        """
        score = 0.0
        factors = []
        
        # 这里可以基于用户历史行为进行风险评估
        # 简化实现，基于一些启发式规则
        
        # 检查是否为异常时间操作
        from datetime import datetime
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 22:  # 非工作时间
            score += 0.2
            factors.append({
                "name": "unusual_time_operation",
                "description": f"非工作时间操作: {current_hour}:00",
                "severity": "low"
            })
        
        # 检查操作复杂度
        intent = getattr(parsed_command.primary_intent, 'intent', '').value if hasattr(parsed_command, 'primary_intent') and parsed_command.primary_intent and hasattr(getattr(parsed_command.primary_intent, 'intent', ''), 'value') else ''
        if len(intent.split()) > 10:  # 复杂指令
            score += 0.1
            factors.append({
                "name": "complex_operation",
                "description": "复杂操作指令",
                "severity": "low"
            })
        
        return {"score": score, "factors": factors}
    
    def _is_external_domain(self, domain: str) -> bool:
        """检查是否为外部域名
        
        Args:
            domain: 域名
            
        Returns:
            是否为外部域名
        """
        # 简化实现，假设所有非本地域名都是外部域名
        local_domains = ["localhost", "127.0.0.1", "0.0.0.0"]
        return domain not in local_domains and not domain.endswith(".local")
    
    def _generate_recommendations(self, factors: List[Dict[str, Any]], 
                                risk_level: RiskLevel) -> List[str]:
        """生成风险缓解建议
        
        Args:
            factors: 风险因子列表
            risk_level: 风险级别
            
        Returns:
            建议列表
        """
        recommendations = []
        
        if risk_level == RiskLevel.CRITICAL:
            recommendations.append("建议停止操作并进行人工审查")
            recommendations.append("启用多因子认证")
        elif risk_level == RiskLevel.HIGH:
            recommendations.append("需要管理员审批")
            recommendations.append("增强监控和日志记录")
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.append("建议增加操作确认步骤")
            recommendations.append("记录详细审计日志")
        
        # 基于具体风险因子的建议
        for factor in factors:
            if factor["name"] == "blacklisted_domain":
                recommendations.append("禁止访问黑名单域名")
            elif factor["name"] == "sensitive_data_detected":
                recommendations.append("对敏感数据进行脱敏处理")
            elif factor["name"] == "high_risk_action":
                recommendations.append("对高风险操作进行二次确认")
        
        return list(set(recommendations))  # 去重
    
    def add_domain_to_blacklist(self, domain: str):
        """添加域名到黑名单
        
        Args:
            domain: 域名
        """
        if domain not in self.domain_blacklist:
            self.domain_blacklist.append(domain)
            logger.info(f"Added domain to blacklist: {domain}")
    
    def remove_domain_from_blacklist(self, domain: str) -> bool:
        """从黑名单移除域名
        
        Args:
            domain: 域名
            
        Returns:
            是否成功移除
        """
        if domain in self.domain_blacklist:
            self.domain_blacklist.remove(domain)
            logger.info(f"Removed domain from blacklist: {domain}")
            return True
        return False
    
    def get_risk_stats(self) -> Dict[str, Any]:
        """获取风险统计信息
        
        Returns:
            统计信息
        """
        return {
            "total_risk_factors": len(self.risk_factors),
            "risk_categories": {
                category.value: len([f for f in self.risk_factors if f.category == category])
                for category in RiskCategory
            },
            "blacklisted_domains": len(self.domain_blacklist),
            "sensitive_patterns": len(self.sensitive_patterns)
        }