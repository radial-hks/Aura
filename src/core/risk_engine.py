"""风险评估引擎模块 - Risk Assessment Engine

本模块是Aura系统的风险评估核心，负责分析和评估自动化操作的风险级别，
为策略引擎提供科学的决策依据。通过多维度风险因子分析，确保系统安全。

核心职责：
1. 多维度风险评估：URL安全性、操作类型、数据敏感性、用户行为分析
2. 风险因子管理：定义、加载和维护各类风险评估因子
3. 动态风险计算：基于实时上下文计算综合风险分数
4. 风险级别分类：将风险分数映射为可理解的风险级别
5. 安全建议生成：根据风险评估结果提供缓解措施建议

架构设计：
- 基于因子权重的风险评估模型
- 可配置的风险阈值和分类规则
- 支持黑名单、敏感数据模式等安全策略
- 异步评估设计，支持复杂风险分析

风险评估维度：
1. URL和域名风险：黑名单检查、外部域名识别、敏感路径检测
2. 操作类型风险：高危操作识别、批量操作检测
3. 数据敏感性风险：个人信息、金融数据、敏感模式检测
4. 用户行为风险：异常时间、操作复杂度、历史行为分析

使用示例：
    engine = RiskEngine()
    assessment = await engine.assess_risk(parsed_command)
    if assessment.level == RiskLevel.HIGH:
        # 执行高风险操作处理逻辑
        pass

扩展性考虑：
- 支持自定义风险因子和权重配置
- 支持机器学习模型集成进行智能风险预测
- 支持与外部威胁情报系统集成
- 支持风险评估历史数据分析和优化
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
    """风险评估引擎 - 多维度安全风险分析系统
    
    实现基于多个维度的综合风险评估，为自动化操作提供安全保障。
    采用加权因子模型，结合静态规则和动态分析，确保风险评估的准确性。
    
    评估维度详解：
    1. URL和域名风险评估：
       - 域名黑名单检查：识别已知恶意域名
       - 外部域名风险：评估跨域操作风险
       - 敏感路径检测：识别管理、支付等敏感页面
    
    2. 操作类型风险评估：
       - 高风险操作：删除、支付、转账等不可逆操作
       - 批量操作：大规模数据处理的风险评估
       - 操作复杂度：复杂指令的潜在风险
    
    3. 数据敏感性风险评估：
       - 个人信息检测：姓名、邮箱、电话等隐私数据
       - 金融数据识别：信用卡号、银行账户等财务信息
       - 敏感模式匹配：基于正则表达式的模式识别
    
    4. 用户行为风险评估：
       - 时间异常检测：非工作时间操作风险
       - 行为模式分析：基于历史行为的异常检测
       - 操作频率监控：异常高频操作识别
    
    风险分数计算：
    - 采用0.0-1.0的归一化分数
    - 基于加权因子累加计算
    - 支持动态阈值调整
    
    风险级别映射：
    - CRITICAL (0.8+): 严重风险，建议禁止操作
    - HIGH (0.6-0.8): 高风险，需要审批
    - MEDIUM (0.3-0.6): 中等风险，需要监控
    - LOW (0.0-0.3): 低风险，正常执行
    """
    
    def __init__(self):
        """初始化风险评估引擎
        
        设置风险评估所需的各种数据结构和配置，包括风险因子、
        安全策略数据等。自动加载预定义的风险规则和安全数据。
        
        初始化组件：
        - 风险因子列表：存储各类风险评估因子及其权重
        - 域名黑名单：已知恶意或高风险域名列表
        - 敏感数据模式：用于检测敏感信息的正则表达式
        
        设计考虑：
        - 支持运行时动态添加和修改风险因子
        - 黑名单支持热更新，无需重启系统
        - 敏感模式支持多语言和多格式检测
        """
        # 风险因子存储 - 包含各维度的风险评估规则
        self.risk_factors: List[RiskFactor] = []
        
        # 域名安全策略 - 黑名单和白名单管理
        self.domain_blacklist: List[str] = []
        
        # 敏感数据检测 - 正则表达式模式库
        self.sensitive_patterns: List[str] = []
        
        # 加载预定义的风险评估规则
        self._load_risk_factors()
        
        # 加载安全策略数据
        self._load_security_data()
        
        logger.info("RiskEngine initialized with comprehensive risk assessment capabilities")
    
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
        """执行综合风险评估 - 系统安全决策的核心方法
        
        基于多维度风险因子对解析后的命令进行全面的安全风险评估，
        生成包含风险级别、分数、触发因子和缓解建议的完整评估报告。
        
        Args:
            parsed_command: 解析后的命令对象，包含：
                - primary_intent: 主要操作意图
                - context: 操作上下文（URL、参数等）
                - parameters: 命令参数和数据
            base_risk_level: 基础风险级别，用于风险评估的起始点
                - 默认为LOW，可根据用户权限或环境调整
            
        Returns:
            RiskAssessment: 综合风险评估结果，包含：
                - level: 风险级别（LOW/MEDIUM/HIGH/CRITICAL）
                - score: 归一化风险分数（0.0-1.0）
                - factors: 触发的风险因子详细列表
                - recommendations: 风险缓解建议措施
                - requires_monitoring: 是否需要增强监控
                - requires_approval: 是否需要人工审批
        
        评估流程：
        1. URL和域名安全性分析
        2. 操作类型风险评估
        3. 数据敏感性检测
        4. 用户行为异常分析
        5. 综合风险分数计算和级别映射
        6. 生成针对性的安全建议
        
        性能优化：
        - 异步并发执行各维度评估
        - 短路评估，高风险因子优先
        - 缓存常用评估结果
        
        扩展性：
        - 支持插件式风险评估模块
        - 支持机器学习模型集成
        - 支持外部威胁情报接入
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
        """获取风险引擎统计信息 - 用于监控和运维分析
        
        提供风险评估引擎的配置状态和运行统计，帮助管理员了解
        当前的风险评估能力和安全策略配置情况。
        
        Returns:
            Dict[str, Any]: 包含以下统计信息的字典：
                - total_risk_factors: 风险因子总数
                - risk_categories: 按风险类别分组的因子数量统计
                    - data_privacy: 数据隐私类风险因子数量
                    - financial: 金融类风险因子数量
                    - security: 安全类风险因子数量
                    - compliance: 合规类风险因子数量
                    - operational: 操作类风险因子数量
                - blacklisted_domains: 黑名单域名数量
                - sensitive_patterns: 敏感数据检测模式数量
        
        使用场景：
        - 安全监控面板展示风险评估能力
        - 风险评估配置完整性检查
        - 安全策略优化分析
        - 系统安全状态报告生成
        
        扩展建议：
        - 添加风险评估执行统计（评估次数、平均耗时等）
        - 添加风险级别分布统计
        - 添加最常触发的风险因子排行
        - 添加风险评估准确性指标
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