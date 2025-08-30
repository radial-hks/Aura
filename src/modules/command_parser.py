"""指令解析与路由决策模块

负责解析用户的自然语言指令，理解用户意图，并决定最佳的执行策略。

主要功能：
- 自然语言指令解析
- 意图识别和参数提取
- 执行策略决策（AI模式 vs 脚本模式）
- 指令队列管理
- 上下文理解和会话管理
"""

import re
import json
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
import difflib
from urllib.parse import urlparse


class IntentType(Enum):
    """意图类型"""
    NAVIGATE = "navigate"  # 导航
    SEARCH = "search"  # 搜索
    CLICK = "click"  # 点击
    FILL_FORM = "fill_form"  # 填写表单
    EXTRACT_DATA = "extract_data"  # 提取数据
    LOGIN = "login"  # 登录
    PURCHASE = "purchase"  # 购买
    DOWNLOAD = "download"  # 下载
    UPLOAD = "upload"  # 上传
    SCROLL = "scroll"  # 滚动
    WAIT = "wait"  # 等待
    ASSERT = "assert"  # 断言验证
    CUSTOM = "custom"  # 自定义操作
    UNKNOWN = "unknown"  # 未知意图


class ExecutionMode(Enum):
    """执行模式"""
    AI_AGENT = "ai_agent"  # AI智能体模式
    FIXED_SCRIPT = "fixed_script"  # 固定脚本模式
    HYBRID = "hybrid"  # 混合模式
    MANUAL_APPROVAL = "manual_approval"  # 需要人工确认


class ConfidenceLevel(Enum):
    """置信度级别"""
    VERY_HIGH = "very_high"  # 0.9+
    HIGH = "high"  # 0.7-0.9
    MEDIUM = "medium"  # 0.5-0.7
    LOW = "low"  # 0.3-0.5
    VERY_LOW = "very_low"  # <0.3


class Priority(Enum):
    """优先级"""
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class ParsedParameter:
    """解析的参数"""
    name: str
    value: Any
    type: str  # string, number, boolean, url, selector, etc.
    confidence: float = 1.0
    source: str = "extracted"  # extracted, inferred, default
    validation_passed: bool = True
    validation_message: Optional[str] = None


@dataclass
class IntentMatch:
    """意图匹配结果"""
    intent: IntentType
    confidence: float
    parameters: List[ParsedParameter] = field(default_factory=list)
    matched_patterns: List[str] = field(default_factory=list)
    context_clues: List[str] = field(default_factory=list)


@dataclass
class SkillMatch:
    """技能匹配结果"""
    skill_id: str
    skill_name: str
    confidence: float
    parameter_mapping: Dict[str, str] = field(default_factory=dict)
    missing_parameters: List[str] = field(default_factory=list)
    domain_match: bool = False
    url_match: bool = False


@dataclass
class ExecutionStrategy:
    """执行策略"""
    mode: ExecutionMode
    confidence: float
    reasoning: str
    skill_match: Optional[SkillMatch] = None
    fallback_mode: Optional[ExecutionMode] = None
    estimated_complexity: str = "medium"  # low, medium, high
    estimated_duration: int = 30  # seconds
    risk_level: str = "low"  # low, medium, high


@dataclass
class ParsedCommand:
    """解析后的指令"""
    original_text: str
    normalized_text: str
    intent_matches: List[IntentMatch] = field(default_factory=list)
    primary_intent: Optional[IntentMatch] = None
    execution_strategy: Optional[ExecutionStrategy] = None
    context: Dict[str, Any] = field(default_factory=dict)
    priority: Priority = Priority.NORMAL
    requires_confirmation: bool = False
    estimated_tokens: int = 0
    parse_time: datetime = field(default_factory=datetime.now)


@dataclass
class ConversationContext:
    """会话上下文"""
    session_id: str
    user_id: Optional[str] = None
    current_url: Optional[str] = None
    current_domain: Optional[str] = None
    page_title: Optional[str] = None
    previous_commands: List[ParsedCommand] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)


class CommandParser:
    """指令解析器"""
    
    def __init__(self, skill_library=None, llm_client=None):
        self.skill_library = skill_library
        self.llm_client = llm_client
        
        # 意图识别模式
        self.intent_patterns = self._load_intent_patterns()
        self.parameter_extractors = self._load_parameter_extractors()
        
        # 会话管理
        self.active_contexts: Dict[str, ConversationContext] = {}
        
        # 统计信息
        self.parse_stats = {
            "total_parsed": 0,
            "successful_matches": 0,
            "ai_mode_selected": 0,
            "script_mode_selected": 0,
            "avg_confidence": 0.0
        }
    
    def _load_intent_patterns(self) -> Dict[IntentType, List[Dict[str, Any]]]:
        """加载意图识别模式"""
        return {
            IntentType.NAVIGATE: [
                {"pattern": r"(打开|访问|进入|跳转到?)\s*(.+)", "confidence": 0.9},
                {"pattern": r"(去|到)\s*(.+?)\s*(网站|页面|链接)?", "confidence": 0.8},
                {"pattern": r"navigate to (.+)", "confidence": 0.9},
                {"pattern": r"go to (.+)", "confidence": 0.8},
                {"pattern": r"open (.+)", "confidence": 0.7}
            ],
            IntentType.SEARCH: [
                {"pattern": r"搜索\s*(.+)", "confidence": 0.9},
                {"pattern": r"查找\s*(.+)", "confidence": 0.8},
                {"pattern": r"找\s*(.+)", "confidence": 0.7},
                {"pattern": r"search (for\s+)?(.+)", "confidence": 0.9},
                {"pattern": r"find (.+)", "confidence": 0.8},
                {"pattern": r"look for (.+)", "confidence": 0.7}
            ],
            IntentType.CLICK: [
                {"pattern": r"点击\s*(.+)", "confidence": 0.9},
                {"pattern": r"按\s*(.+)", "confidence": 0.8},
                {"pattern": r"选择\s*(.+)", "confidence": 0.7},
                {"pattern": r"click (on\s+)?(.+)", "confidence": 0.9},
                {"pattern": r"press (.+)", "confidence": 0.8},
                {"pattern": r"select (.+)", "confidence": 0.7}
            ],
            IntentType.FILL_FORM: [
                {"pattern": r"填写\s*(.+?)\s*(为|是|:)\s*(.+)", "confidence": 0.9},
                {"pattern": r"输入\s*(.+?)\s*(为|是|:)\s*(.+)", "confidence": 0.8},
                {"pattern": r"在\s*(.+?)\s*(中|里)\s*(输入|填入)\s*(.+)", "confidence": 0.8},
                {"pattern": r"fill (.+?) with (.+)", "confidence": 0.9},
                {"pattern": r"enter (.+?) in(to)?\s+(.+)", "confidence": 0.8},
                {"pattern": r"type (.+?) in(to)?\s+(.+)", "confidence": 0.8}
            ],
            IntentType.LOGIN: [
                {"pattern": r"登录\s*(用户名|账号)?\s*(.+?)\s*(密码)?\s*(.+)?", "confidence": 0.9},
                {"pattern": r"用\s*(.+?)\s*(和|,)\s*(.+?)\s*登录", "confidence": 0.8},
                {"pattern": r"login with (.+?) and (.+)", "confidence": 0.9},
                {"pattern": r"sign in (.+)", "confidence": 0.8}
            ],
            IntentType.EXTRACT_DATA: [
                {"pattern": r"提取\s*(.+)", "confidence": 0.8},
                {"pattern": r"获取\s*(.+)", "confidence": 0.8},
                {"pattern": r"抓取\s*(.+)", "confidence": 0.7},
                {"pattern": r"extract (.+)", "confidence": 0.8},
                {"pattern": r"get (.+?) (data|information|content)", "confidence": 0.8},
                {"pattern": r"scrape (.+)", "confidence": 0.7}
            ],
            IntentType.WAIT: [
                {"pattern": r"等待\s*(\d+)\s*(秒|分钟)?", "confidence": 0.9},
                {"pattern": r"等\s*(.+?)\s*(出现|加载|完成)", "confidence": 0.8},
                {"pattern": r"wait (for\s+)?(\d+)\s*(seconds?|minutes?)?", "confidence": 0.9},
                {"pattern": r"wait (for\s+)?(.+?) to (appear|load|complete)", "confidence": 0.8}
            ]
        }
    
    def _load_parameter_extractors(self) -> Dict[str, Dict[str, Any]]:
        """加载参数提取器"""
        return {
            "url": {
                "pattern": r"https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9-]+\.[a-zA-Z]{2,}[^\s]*",
                "type": "url",
                "validator": self._validate_url
            },
            "number": {
                "pattern": r"\b\d+(?:\.\d+)?\b",
                "type": "number",
                "converter": lambda x: float(x) if '.' in x else int(x)
            },
            "selector": {
                "pattern": r"#[a-zA-Z][a-zA-Z0-9_-]*|\.[a-zA-Z][a-zA-Z0-9_-]*|\[[^\]]+\]",
                "type": "selector"
            },
            "email": {
                "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                "type": "email"
            },
            "time_duration": {
                "pattern": r"(\d+)\s*(秒|分钟|小时|seconds?|minutes?|hours?)",
                "type": "duration",
                "converter": self._convert_duration
            }
        }
    
    def _validate_url(self, url: str) -> bool:
        """验证URL格式"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def _convert_duration(self, match_groups: Tuple[str, str]) -> int:
        """转换时间持续时间为秒"""
        value, unit = match_groups
        value = int(value)
        
        unit_multipliers = {
            "秒": 1, "seconds": 1, "second": 1,
            "分钟": 60, "minutes": 60, "minute": 60,
            "小时": 3600, "hours": 3600, "hour": 3600
        }
        
        return value * unit_multipliers.get(unit.lower(), 1)
    
    async def parse_command(self, command_text: str, context: Optional[ConversationContext] = None) -> ParsedCommand:
        """解析指令"""
        start_time = datetime.now()
        
        # 标准化文本
        normalized_text = self._normalize_text(command_text)
        
        # 创建解析结果
        parsed_command = ParsedCommand(
            original_text=command_text,
            normalized_text=normalized_text
        )
        
        # 意图识别
        intent_matches = await self._identify_intents(normalized_text, context)
        parsed_command.intent_matches = intent_matches
        
        # 选择主要意图
        if intent_matches:
            parsed_command.primary_intent = max(intent_matches, key=lambda x: x.confidence)
        
        # 参数提取
        if parsed_command.primary_intent:
            await self._extract_parameters(parsed_command, context)
        
        # 执行策略决策
        execution_strategy = await self._decide_execution_strategy(parsed_command, context)
        parsed_command.execution_strategy = execution_strategy
        
        # 风险评估
        parsed_command.requires_confirmation = self._assess_risk(parsed_command)
        
        # 估算Token消耗
        parsed_command.estimated_tokens = self._estimate_tokens(parsed_command)
        
        # 更新统计
        self._update_stats(parsed_command)
        
        # 更新上下文
        if context:
            context.previous_commands.append(parsed_command)
            context.last_activity = datetime.now()
        
        return parsed_command
    
    def _normalize_text(self, text: str) -> str:
        """标准化文本"""
        # 去除多余空格
        text = re.sub(r'\s+', ' ', text.strip())
        
        # 统一标点符号
        text = text.replace('，', ',').replace('。', '.').replace('？', '?').replace('！', '!')
        
        # 转换常见缩写
        abbreviations = {
            "网址": "URL",
            "链接": "link",
            "按钮": "button",
            "输入框": "input",
            "文本框": "textbox"
        }
        
        for abbr, full in abbreviations.items():
            text = text.replace(abbr, full)
        
        return text
    
    async def _identify_intents(self, text: str, context: Optional[ConversationContext] = None) -> List[IntentMatch]:
        """识别意图"""
        matches = []
        
        # 基于模式匹配
        for intent_type, patterns in self.intent_patterns.items():
            for pattern_info in patterns:
                pattern = pattern_info["pattern"]
                base_confidence = pattern_info["confidence"]
                
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # 上下文增强
                    context_boost = self._calculate_context_boost(intent_type, context)
                    final_confidence = min(base_confidence + context_boost, 1.0)
                    
                    intent_match = IntentMatch(
                        intent=intent_type,
                        confidence=final_confidence,
                        matched_patterns=[pattern],
                        context_clues=self._extract_context_clues(text, context)
                    )
                    matches.append(intent_match)
        
        # 使用LLM进行高级意图识别（如果可用）
        if self.llm_client and not matches:
            llm_intent = await self._llm_intent_identification(text, context)
            if llm_intent:
                matches.append(llm_intent)
        
        # 去重和排序
        matches = self._deduplicate_intents(matches)
        matches.sort(key=lambda x: x.confidence, reverse=True)
        
        return matches
    
    def _calculate_context_boost(self, intent_type: IntentType, context: Optional[ConversationContext]) -> float:
        """计算上下文增强分数"""
        if not context:
            return 0.0
        
        boost = 0.0
        
        # 基于当前页面的增强
        if context.current_domain:
            domain_intent_mapping = {
                "search": [IntentType.SEARCH],
                "shop": [IntentType.PURCHASE, IntentType.SEARCH],
                "login": [IntentType.LOGIN],
                "form": [IntentType.FILL_FORM]
            }
            
            for keyword, intents in domain_intent_mapping.items():
                if keyword in context.current_domain.lower() and intent_type in intents:
                    boost += 0.1
        
        # 基于历史指令的增强
        if context.previous_commands:
            recent_intents = [cmd.primary_intent.intent for cmd in context.previous_commands[-3:] 
                            if cmd.primary_intent]
            
            # 连续相同意图的增强
            if recent_intents and recent_intents[-1] == intent_type:
                boost += 0.05
        
        return boost
    
    def _extract_context_clues(self, text: str, context: Optional[ConversationContext]) -> List[str]:
        """提取上下文线索"""
        clues = []
        
        # 时间相关线索
        time_patterns = ["现在", "立即", "马上", "稍后", "然后", "接下来"]
        for pattern in time_patterns:
            if pattern in text:
                clues.append(f"temporal:{pattern}")
        
        # 位置相关线索
        location_patterns = ["这里", "那里", "上面", "下面", "左边", "右边"]
        for pattern in location_patterns:
            if pattern in text:
                clues.append(f"spatial:{pattern}")
        
        # 引用相关线索
        reference_patterns = ["这个", "那个", "它", "他们"]
        for pattern in reference_patterns:
            if pattern in text:
                clues.append(f"reference:{pattern}")
        
        return clues
    
    async def _llm_intent_identification(self, text: str, context: Optional[ConversationContext]) -> Optional[IntentMatch]:
        """使用LLM进行意图识别"""
        if not self.llm_client:
            return None
        
        try:
            prompt = f"""
            请分析以下用户指令的意图：
            
            指令：{text}
            
            可能的意图类型：
            - navigate: 导航到页面
            - search: 搜索内容
            - click: 点击元素
            - fill_form: 填写表单
            - extract_data: 提取数据
            - login: 登录
            - purchase: 购买
            - download: 下载
            - upload: 上传
            - scroll: 滚动
            - wait: 等待
            - assert: 断言验证
            - custom: 自定义操作
            
            请返回JSON格式：
            {{
                "intent": "意图类型",
                "confidence": 0.8,
                "reasoning": "判断理由"
            }}
            """
            
            response = await self.llm_client.complete(prompt)
            result = json.loads(response)
            
            intent_type = IntentType(result["intent"])
            confidence = float(result["confidence"])
            
            return IntentMatch(
                intent=intent_type,
                confidence=confidence,
                context_clues=[f"llm_reasoning:{result['reasoning']}"]
            )
            
        except Exception as e:
            print(f"LLM intent identification failed: {str(e)}")
            return None
    
    def _deduplicate_intents(self, matches: List[IntentMatch]) -> List[IntentMatch]:
        """去重意图匹配"""
        intent_map = {}
        
        for match in matches:
            if match.intent not in intent_map or match.confidence > intent_map[match.intent].confidence:
                intent_map[match.intent] = match
        
        return list(intent_map.values())
    
    async def _extract_parameters(self, parsed_command: ParsedCommand, context: Optional[ConversationContext]):
        """提取参数"""
        if not parsed_command.primary_intent:
            return
        
        text = parsed_command.normalized_text
        intent = parsed_command.primary_intent.intent
        parameters = []
        
        # 基于意图类型的特定参数提取
        if intent == IntentType.NAVIGATE:
            url_param = self._extract_url_parameter(text)
            if url_param:
                parameters.append(url_param)
        
        elif intent == IntentType.SEARCH:
            query_param = self._extract_search_query(text)
            if query_param:
                parameters.append(query_param)
        
        elif intent == IntentType.FILL_FORM:
            form_params = self._extract_form_parameters(text)
            parameters.extend(form_params)
        
        elif intent == IntentType.WAIT:
            duration_param = self._extract_duration_parameter(text)
            if duration_param:
                parameters.append(duration_param)
        
        # 通用参数提取
        generic_params = self._extract_generic_parameters(text)
        parameters.extend(generic_params)
        
        # 参数验证
        validated_params = []
        for param in parameters:
            if self._validate_parameter(param):
                validated_params.append(param)
            else:
                param.validation_passed = False
                validated_params.append(param)
        
        parsed_command.primary_intent.parameters = validated_params
    
    def _extract_url_parameter(self, text: str) -> Optional[ParsedParameter]:
        """提取URL参数"""
        url_pattern = self.parameter_extractors["url"]["pattern"]
        match = re.search(url_pattern, text)
        
        if match:
            url = match.group(0)
            # 补全协议
            if not url.startswith(('http://', 'https://')):
                if url.startswith('www.'):
                    url = 'https://' + url
                else:
                    url = 'https://' + url
            
            return ParsedParameter(
                name="url",
                value=url,
                type="url",
                confidence=0.9 if self._validate_url(url) else 0.5
            )
        
        return None
    
    def _extract_search_query(self, text: str) -> Optional[ParsedParameter]:
        """提取搜索查询"""
        # 移除搜索关键词
        search_keywords = ["搜索", "查找", "找", "search", "find", "look for"]
        
        for keyword in search_keywords:
            pattern = rf"{keyword}\s+(.+)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                query = match.group(1).strip()
                return ParsedParameter(
                    name="query",
                    value=query,
                    type="string",
                    confidence=0.9
                )
        
        return None
    
    def _extract_form_parameters(self, text: str) -> List[ParsedParameter]:
        """提取表单参数"""
        parameters = []
        
        # 匹配 "字段名 为/是 值" 的模式
        pattern = r"(\w+)\s*(为|是|:|=)\s*([^,，]+)"
        matches = re.findall(pattern, text)
        
        for field_name, separator, value in matches:
            parameters.append(ParsedParameter(
                name=field_name.strip(),
                value=value.strip(),
                type="string",
                confidence=0.8
            ))
        
        return parameters
    
    def _extract_duration_parameter(self, text: str) -> Optional[ParsedParameter]:
        """提取时间持续参数"""
        duration_pattern = self.parameter_extractors["time_duration"]["pattern"]
        match = re.search(duration_pattern, text)
        
        if match:
            duration_seconds = self._convert_duration(match.groups())
            return ParsedParameter(
                name="duration",
                value=duration_seconds,
                type="duration",
                confidence=0.9
            )
        
        return None
    
    def _extract_generic_parameters(self, text: str) -> List[ParsedParameter]:
        """提取通用参数"""
        parameters = []
        
        # 提取数字
        for match in re.finditer(self.parameter_extractors["number"]["pattern"], text):
            value = match.group(0)
            converted_value = float(value) if '.' in value else int(value)
            parameters.append(ParsedParameter(
                name="number",
                value=converted_value,
                type="number",
                confidence=0.7
            ))
        
        # 提取选择器
        for match in re.finditer(self.parameter_extractors["selector"]["pattern"], text):
            selector = match.group(0)
            parameters.append(ParsedParameter(
                name="selector",
                value=selector,
                type="selector",
                confidence=0.8
            ))
        
        # 提取邮箱
        for match in re.finditer(self.parameter_extractors["email"]["pattern"], text):
            email = match.group(0)
            parameters.append(ParsedParameter(
                name="email",
                value=email,
                type="email",
                confidence=0.9
            ))
        
        return parameters
    
    def _validate_parameter(self, param: ParsedParameter) -> bool:
        """验证参数"""
        if param.type == "url":
            return self._validate_url(param.value)
        elif param.type == "email":
            return re.match(self.parameter_extractors["email"]["pattern"], param.value) is not None
        elif param.type == "number":
            return isinstance(param.value, (int, float))
        
        return True
    
    async def _decide_execution_strategy(self, parsed_command: ParsedCommand, 
                                       context: Optional[ConversationContext]) -> ExecutionStrategy:
        """决定执行策略"""
        if not parsed_command.primary_intent:
            return ExecutionStrategy(
                mode=ExecutionMode.AI_AGENT,
                confidence=0.5,
                reasoning="No clear intent identified, defaulting to AI agent mode"
            )
        
        intent = parsed_command.primary_intent.intent
        confidence = parsed_command.primary_intent.confidence
        
        # 查找匹配的技能
        skill_matches = await self._find_matching_skills(parsed_command, context)
        
        if skill_matches:
            best_skill = max(skill_matches, key=lambda x: x.confidence)
            
            if best_skill.confidence > 0.8 and confidence > 0.7:
                return ExecutionStrategy(
                    mode=ExecutionMode.FIXED_SCRIPT,
                    confidence=min(best_skill.confidence, confidence),
                    reasoning=f"High confidence skill match: {best_skill.skill_name}",
                    skill_match=best_skill,
                    fallback_mode=ExecutionMode.AI_AGENT
                )
            elif best_skill.confidence > 0.6:
                return ExecutionStrategy(
                    mode=ExecutionMode.HYBRID,
                    confidence=best_skill.confidence * 0.8,
                    reasoning=f"Medium confidence skill match: {best_skill.skill_name}",
                    skill_match=best_skill,
                    fallback_mode=ExecutionMode.AI_AGENT
                )
        
        # 基于意图复杂度决策
        complexity_scores = {
            IntentType.NAVIGATE: 0.2,
            IntentType.CLICK: 0.3,
            IntentType.SEARCH: 0.4,
            IntentType.FILL_FORM: 0.6,
            IntentType.LOGIN: 0.7,
            IntentType.EXTRACT_DATA: 0.8,
            IntentType.PURCHASE: 0.9,
            IntentType.CUSTOM: 1.0
        }
        
        complexity = complexity_scores.get(intent, 0.5)
        
        if complexity < 0.5 and confidence > 0.8:
            mode = ExecutionMode.AI_AGENT
            reasoning = "Simple operation with high confidence"
        elif complexity > 0.7:
            mode = ExecutionMode.MANUAL_APPROVAL
            reasoning = "Complex operation requiring manual approval"
        else:
            mode = ExecutionMode.AI_AGENT
            reasoning = "Default to AI agent mode"
        
        return ExecutionStrategy(
            mode=mode,
            confidence=confidence,
            reasoning=reasoning,
            estimated_complexity="high" if complexity > 0.7 else "medium" if complexity > 0.4 else "low",
            risk_level="high" if complexity > 0.8 else "medium" if complexity > 0.5 else "low"
        )
    
    async def _find_matching_skills(self, parsed_command: ParsedCommand, 
                                  context: Optional[ConversationContext]) -> List[SkillMatch]:
        """查找匹配的技能"""
        if not self.skill_library:
            return []
        
        matches = []
        intent = parsed_command.primary_intent.intent
        
        # 基于当前域名查找技能
        domain = None
        if context and context.current_domain:
            domain = context.current_domain
        
        # 查找相关技能
        skills = self.skill_library.find_skills(
            domain=domain,
            tags=[intent.value] if intent != IntentType.UNKNOWN else None
        )
        
        for skill in skills:
            # 计算匹配度
            confidence = self._calculate_skill_match_confidence(skill, parsed_command, context)
            
            if confidence > 0.3:  # 最低阈值
                # 检查参数映射
                parameter_mapping, missing_params = self._map_skill_parameters(skill, parsed_command)
                
                skill_match = SkillMatch(
                    skill_id=skill.id,
                    skill_name=skill.name,
                    confidence=confidence,
                    parameter_mapping=parameter_mapping,
                    missing_parameters=missing_params,
                    domain_match=domain in skill.target_domains if domain else False,
                    url_match=self._check_url_match(skill, context)
                )
                matches.append(skill_match)
        
        return sorted(matches, key=lambda x: x.confidence, reverse=True)
    
    def _calculate_skill_match_confidence(self, skill, parsed_command: ParsedCommand, 
                                        context: Optional[ConversationContext]) -> float:
        """计算技能匹配置信度"""
        confidence = 0.0
        
        # 基础意图匹配
        intent = parsed_command.primary_intent.intent
        if intent.value in skill.tags:
            confidence += 0.4
        
        # 域名匹配
        if context and context.current_domain:
            if context.current_domain in skill.target_domains:
                confidence += 0.3
            elif any(domain in context.current_domain for domain in skill.target_domains):
                confidence += 0.2
        
        # URL匹配
        if context and context.current_url:
            for target_url in skill.target_urls:
                if target_url in context.current_url:
                    confidence += 0.2
                    break
        
        # 参数匹配
        available_params = {p.name for p in parsed_command.primary_intent.parameters}
        required_params = {inp.name for inp in skill.inputs if inp.required}
        
        if required_params:
            param_match_ratio = len(available_params.intersection(required_params)) / len(required_params)
            confidence += param_match_ratio * 0.3
        
        # 技能评分加成
        if skill.rating > 4.0:
            confidence += 0.1
        elif skill.rating > 3.0:
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def _map_skill_parameters(self, skill, parsed_command: ParsedCommand) -> Tuple[Dict[str, str], List[str]]:
        """映射技能参数"""
        parameter_mapping = {}
        missing_parameters = []
        
        available_params = {p.name: p.value for p in parsed_command.primary_intent.parameters}
        
        for skill_input in skill.inputs:
            if skill_input.name in available_params:
                parameter_mapping[skill_input.name] = available_params[skill_input.name]
            elif skill_input.required:
                missing_parameters.append(skill_input.name)
        
        return parameter_mapping, missing_parameters
    
    def _check_url_match(self, skill, context: Optional[ConversationContext]) -> bool:
        """检查URL匹配"""
        if not context or not context.current_url:
            return False
        
        for target_url in skill.target_urls:
            if target_url in context.current_url:
                return True
        
        return False
    
    def _assess_risk(self, parsed_command: ParsedCommand) -> bool:
        """评估风险"""
        if not parsed_command.primary_intent:
            return False
        
        high_risk_intents = [
            IntentType.PURCHASE,
            IntentType.LOGIN,
            IntentType.UPLOAD,
            IntentType.FILL_FORM
        ]
        
        # 高风险意图
        if parsed_command.primary_intent.intent in high_risk_intents:
            return True
        
        # 检查敏感参数
        sensitive_patterns = ["password", "credit", "card", "payment", "bank"]
        text_lower = parsed_command.normalized_text.lower()
        
        for pattern in sensitive_patterns:
            if pattern in text_lower:
                return True
        
        return False
    
    def _estimate_tokens(self, parsed_command: ParsedCommand) -> int:
        """估算Token消耗"""
        base_tokens = len(parsed_command.normalized_text.split()) * 1.3  # 基础token
        
        if parsed_command.execution_strategy:
            if parsed_command.execution_strategy.mode == ExecutionMode.AI_AGENT:
                # AI模式需要更多token
                complexity_multiplier = {
                    "low": 2,
                    "medium": 4,
                    "high": 8
                }.get(parsed_command.execution_strategy.estimated_complexity, 4)
                
                return int(base_tokens * complexity_multiplier)
            else:
                # 脚本模式token消耗较少
                return int(base_tokens * 1.5)
        
        return int(base_tokens * 3)  # 默认估算
    
    def _update_stats(self, parsed_command: ParsedCommand):
        """更新统计信息"""
        self.parse_stats["total_parsed"] += 1
        
        if parsed_command.primary_intent:
            self.parse_stats["successful_matches"] += 1
            
            # 更新平均置信度
            total_confidence = (self.parse_stats["avg_confidence"] * 
                              (self.parse_stats["successful_matches"] - 1) + 
                              parsed_command.primary_intent.confidence)
            self.parse_stats["avg_confidence"] = total_confidence / self.parse_stats["successful_matches"]
        
        if parsed_command.execution_strategy:
            if parsed_command.execution_strategy.mode == ExecutionMode.AI_AGENT:
                self.parse_stats["ai_mode_selected"] += 1
            elif parsed_command.execution_strategy.mode == ExecutionMode.FIXED_SCRIPT:
                self.parse_stats["script_mode_selected"] += 1
    
    def create_context(self, session_id: str, user_id: Optional[str] = None) -> ConversationContext:
        """创建会话上下文"""
        context = ConversationContext(
            session_id=session_id,
            user_id=user_id
        )
        self.active_contexts[session_id] = context
        return context
    
    def get_context(self, session_id: str) -> Optional[ConversationContext]:
        """获取会话上下文"""
        return self.active_contexts.get(session_id)
    
    def update_context(self, session_id: str, **kwargs):
        """更新会话上下文"""
        context = self.get_context(session_id)
        if context:
            for key, value in kwargs.items():
                if hasattr(context, key):
                    setattr(context, key, value)
            context.last_activity = datetime.now()
    
    def cleanup_expired_contexts(self, max_age_hours: int = 24):
        """清理过期的会话上下文"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        expired_sessions = [
            session_id for session_id, context in self.active_contexts.items()
            if context.last_activity < cutoff_time
        ]
        
        for session_id in expired_sessions:
            del self.active_contexts[session_id]
    
    def get_parse_statistics(self) -> Dict[str, Any]:
        """获取解析统计信息"""
        return self.parse_stats.copy()


# 示例使用
if __name__ == "__main__":
    import asyncio
    
    async def main():
        parser = CommandParser()
        
        # 创建会话上下文
        context = parser.create_context("session_001", "user_123")
        context.current_url = "https://example.com"
        context.current_domain = "example.com"
        
        # 测试指令解析
        test_commands = [
            "打开百度网站",
            "搜索Python教程",
            "点击登录按钮",
            "填写用户名为admin，密码为123456",
            "等待5秒钟",
            "提取页面标题"
        ]
        
        for command in test_commands:
            print(f"\n解析指令: {command}")
            parsed = await parser.parse_command(command, context)
            
            print(f"主要意图: {parsed.primary_intent.intent.value if parsed.primary_intent else 'Unknown'}")
            print(f"置信度: {parsed.primary_intent.confidence if parsed.primary_intent else 0}")
            print(f"执行模式: {parsed.execution_strategy.mode.value if parsed.execution_strategy else 'Unknown'}")
            print(f"需要确认: {parsed.requires_confirmation}")
            print(f"估算Token: {parsed.estimated_tokens}")
        
        # 显示统计信息
        stats = parser.get_parse_statistics()
        print(f"\n解析统计: {stats}")
    
    # asyncio.run(main())