"""站点探索与建模引擎

负责自动探索网站结构，生成站点认知地图，并提供语义定位符管理功能。

主要功能：
- 网站结构的自动探索和分析
- 站点模型的生成和版本管理
- 语义定位符的提取和维护
- 导航图的构建和优化
"""

import json
import time
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse


class ExplorationStrategy(Enum):
    """探索策略"""
    BREADTH_FIRST = "breadth_first"  # 广度优先
    DEPTH_FIRST = "depth_first"  # 深度优先
    INTERACTIVE = "interactive"  # 交互式探索
    TARGETED = "targeted"  # 目标导向探索


class ElementType(Enum):
    """元素类型"""
    BUTTON = "button"
    LINK = "link"
    INPUT = "input"
    FORM = "form"
    NAVIGATION = "navigation"
    CONTENT = "content"
    SEARCH = "search"
    LOGIN = "login"
    MENU = "menu"
    MODAL = "modal"


class PageType(Enum):
    """页面类型"""
    HOMEPAGE = "homepage"
    CATEGORY = "category"
    PRODUCT = "product"
    SEARCH_RESULTS = "search_results"
    LOGIN = "login"
    CHECKOUT = "checkout"
    PROFILE = "profile"
    UNKNOWN = "unknown"


@dataclass
class ElementInfo:
    """页面元素信息"""
    id: str
    type: ElementType
    selectors: List[str]  # 多个备用选择器
    text: Optional[str] = None
    purpose: Optional[str] = None
    attributes: Dict[str, str] = field(default_factory=dict)
    position: Optional[Tuple[int, int]] = None  # (x, y) 坐标
    size: Optional[Tuple[int, int]] = None  # (width, height)
    confidence: float = 1.0  # 选择器可靠性
    last_verified: Optional[datetime] = None


@dataclass
class PageInfo:
    """页面信息"""
    url: str
    title: str
    type: PageType
    description: Optional[str] = None
    elements: Dict[str, ElementInfo] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    screenshot_path: Optional[str] = None
    last_explored: Optional[datetime] = None
    exploration_depth: int = 0


@dataclass
class NavigationEdge:
    """导航边"""
    from_page: str
    to_page: str
    trigger_element: str  # 触发导航的元素ID
    action_type: str  # click, submit, etc.
    conditions: List[str] = field(default_factory=list)  # 导航条件
    success_rate: float = 1.0  # 成功率


@dataclass
class SiteModel:
    """站点模型"""
    domain: str
    version: str
    pages: Dict[str, PageInfo] = field(default_factory=dict)
    navigation_graph: List[NavigationEdge] = field(default_factory=list)
    global_elements: Dict[str, ElementInfo] = field(default_factory=dict)  # 全局元素（如导航栏）
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    ttl: timedelta = field(default_factory=lambda: timedelta(days=7))  # 生存时间


@dataclass
class ExplorationTask:
    """探索任务"""
    id: str
    domain: str
    start_url: str
    strategy: ExplorationStrategy
    max_depth: int = 3
    max_pages: int = 50
    timeout: int = 300  # 秒
    target_elements: List[str] = field(default_factory=list)  # 目标元素类型
    exclude_patterns: List[str] = field(default_factory=list)  # 排除的URL模式
    
    # 执行状态
    status: str = "pending"  # pending, running, completed, failed
    progress: float = 0.0
    explored_pages: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None


class SiteExplorer:
    """站点探索引擎"""
    
    def __init__(self, mcp_manager=None):
        self.site_models: Dict[str, SiteModel] = {}  # domain -> model
        self.exploration_queue: List[ExplorationTask] = []
        self.running_tasks: Dict[str, ExplorationTask] = {}
        self.element_classifiers = self._init_element_classifiers()
        self.page_classifiers = self._init_page_classifiers()
        
        # MCP 集成
        self.mcp_manager = mcp_manager
        self._browser_extension_mode = False
        self._active_browser_tabs = {}  # 跟踪活跃的浏览器标签页
    
    def _init_element_classifiers(self) -> Dict[ElementType, List[str]]:
        """初始化元素分类器"""
        return {
            ElementType.BUTTON: [
                'button', 'input[type="button"]', 'input[type="submit"]',
                '.btn', '.button', '[role="button"]'
            ],
            ElementType.LINK: [
                'a[href]', '.link', '[role="link"]'
            ],
            ElementType.INPUT: [
                'input[type="text"]', 'input[type="email"]', 'input[type="password"]',
                'textarea', '.input', '.form-control'
            ],
            ElementType.SEARCH: [
                'input[name*="search"]', 'input[placeholder*="search"]',
                '.search-box', '.search-input', '#search'
            ],
            ElementType.LOGIN: [
                'input[type="password"]', '.login-form', '#login',
                'form[action*="login"]'
            ],
            ElementType.NAVIGATION: [
                'nav', '.navbar', '.navigation', '.menu', '[role="navigation"]'
            ],
            ElementType.MENU: [
                '.menu', '.dropdown', '.nav-menu', '[role="menu"]'
            ]
        }
    
    def _init_page_classifiers(self) -> Dict[PageType, List[str]]:
        """初始化页面分类器"""
        return {
            PageType.HOMEPAGE: [
                'home', 'index', 'main', 'welcome'
            ],
            PageType.PRODUCT: [
                'product', 'item', 'detail', 'shop'
            ],
            PageType.CATEGORY: [
                'category', 'catalog', 'browse', 'collection'
            ],
            PageType.SEARCH_RESULTS: [
                'search', 'results', 'query'
            ],
            PageType.LOGIN: [
                'login', 'signin', 'auth', 'account'
            ],
            PageType.CHECKOUT: [
                'checkout', 'cart', 'order', 'payment'
            ]
        }
    
    async def explore_and_model(self, domain: str, start_url: str = None, strategy: str = "breadth_first", max_depth: int = 3) -> SiteModel:
        """探索并建模站点（简化接口）"""
        if not start_url:
            start_url = f"https://{domain}"
        
        # 创建探索任务
        task = ExplorationTask(
            id=f"explore_{domain}_{int(time.time())}",
            domain=domain,
            start_url=start_url,
            strategy=ExplorationStrategy(strategy),
            max_depth=max_depth
        )
        
        return await self.explore_site(task)
    
    async def explore_site(self, task: ExplorationTask, page_context=None) -> SiteModel:
        """探索站点"""
        task.status = "running"
        task.start_time = datetime.now()
        task.progress = 0.0
        self.running_tasks[task.id] = task
        
        try:
            # 获取或创建站点模型
            model = self.site_models.get(task.domain)
            if not model:
                model = SiteModel(
                    domain=task.domain,
                    version="1.0.0"
                )
                self.site_models[task.domain] = model
            
            # 执行探索
            if task.strategy == ExplorationStrategy.BREADTH_FIRST:
                await self._explore_breadth_first(task, model, page_context)
            elif task.strategy == ExplorationStrategy.DEPTH_FIRST:
                await self._explore_depth_first(task, model, page_context)
            elif task.strategy == ExplorationStrategy.INTERACTIVE:
                await self._explore_interactive(task, model, page_context)
            elif task.strategy == ExplorationStrategy.TARGETED:
                await self._explore_targeted(task, model, page_context)
            
            # 更新模型
            model.last_updated = datetime.now()
            model.version = self._increment_version(model.version)
            
            task.status = "completed"
            task.progress = 1.0
            
        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            raise
        
        finally:
            task.end_time = datetime.now()
            if task.id in self.running_tasks:
                del self.running_tasks[task.id]
        
        return model
    
    async def _explore_breadth_first(self, task: ExplorationTask, model: SiteModel, page_context):
        """广度优先探索"""
        visited_urls = set()
        url_queue = [(task.start_url, 0)]  # (url, depth)
        
        while url_queue and len(visited_urls) < task.max_pages:
            current_url, depth = url_queue.pop(0)
            
            if depth > task.max_depth or current_url in visited_urls:
                continue
            
            if self._should_exclude_url(current_url, task.exclude_patterns):
                continue
            
            # 访问页面
            page_info = await self._explore_page(current_url, page_context)
            if page_info:
                model.pages[current_url] = page_info
                visited_urls.add(current_url)
                task.explored_pages += 1
                
                # 更新进度
                task.progress = min(task.explored_pages / task.max_pages, 1.0)
                
                # 发现新链接
                new_links = self._extract_links(page_info, current_url)
                for link in new_links:
                    if link not in visited_urls:
                        url_queue.append((link, depth + 1))
    
    async def _explore_depth_first(self, task: ExplorationTask, model: SiteModel, page_context):
        """深度优先探索"""
        visited_urls = set()
        
        async def dfs(url: str, depth: int):
            if (depth > task.max_depth or 
                url in visited_urls or 
                len(visited_urls) >= task.max_pages or
                self._should_exclude_url(url, task.exclude_patterns)):
                return
            
            # 访问页面
            page_info = await self._explore_page(url, page_context)
            if page_info:
                model.pages[url] = page_info
                visited_urls.add(url)
                task.explored_pages += 1
                task.progress = min(task.explored_pages / task.max_pages, 1.0)
                
                # 递归访问链接
                new_links = self._extract_links(page_info, url)
                for link in new_links:
                    await dfs(link, depth + 1)
        
        await dfs(task.start_url, 0)
    
    async def _explore_interactive(self, task: ExplorationTask, model: SiteModel, page_context):
        """交互式探索（点击、悬停等）"""
        # 实现交互式探索逻辑
        page_info = await self._explore_page(task.start_url, page_context)
        if page_info:
            model.pages[task.start_url] = page_info
            
            # 尝试交互操作
            await self._perform_interactions(page_info, page_context)
    
    async def _explore_targeted(self, task: ExplorationTask, model: SiteModel, page_context):
        """目标导向探索"""
        # 根据目标元素类型进行有针对性的探索
        page_info = await self._explore_page(task.start_url, page_context)
        if page_info:
            model.pages[task.start_url] = page_info
            
            # 查找目标元素
            for element_type in task.target_elements:
                await self._find_target_elements(element_type, page_info, page_context)
    
    async def _explore_page(self, url: str, page_context) -> Optional[PageInfo]:
        """探索单个页面"""
        try:
            if not page_context:
                # 模拟页面探索（实际需要Playwright MCP）
                return self._create_mock_page_info(url)
            
            # 导航到页面
            # await page_context.goto(url)
            
            # 获取页面信息
            # title = await page_context.title()
            title = f"Mock Title for {url}"
            
            # 分类页面类型
            page_type = self._classify_page_type(url, title)
            
            # 提取元素
            elements = await self._extract_page_elements(page_context)
            
            # 截图
            # screenshot_path = f"screenshot_{int(time.time())}.png"
            # await page_context.screenshot(path=screenshot_path)
            screenshot_path = None
            
            page_info = PageInfo(
                url=url,
                title=title,
                type=page_type,
                elements=elements,
                screenshot_path=screenshot_path,
                last_explored=datetime.now()
            )
            
            return page_info
            
        except Exception as e:
            print(f"Failed to explore page {url}: {str(e)}")
            return None
    
    def _create_mock_page_info(self, url: str) -> PageInfo:
        """创建模拟页面信息（用于测试）"""
        parsed_url = urlparse(url)
        title = f"Mock Page - {parsed_url.path}"
        page_type = self._classify_page_type(url, title)
        
        # 创建一些模拟元素
        elements = {
            "search_box": ElementInfo(
                id="search_box",
                type=ElementType.SEARCH,
                selectors=["#search", ".search-input", "input[name='q']"],
                text="Search",
                purpose="全局搜索功能"
            ),
            "nav_menu": ElementInfo(
                id="nav_menu",
                type=ElementType.NAVIGATION,
                selectors=["nav", ".navbar", ".main-nav"],
                purpose="主导航菜单"
            )
        }
        
        return PageInfo(
            url=url,
            title=title,
            type=page_type,
            elements=elements,
            last_explored=datetime.now()
        )
    
    def _classify_page_type(self, url: str, title: str) -> PageType:
        """分类页面类型"""
        url_lower = url.lower()
        title_lower = title.lower()
        
        for page_type, keywords in self.page_classifiers.items():
            for keyword in keywords:
                if keyword in url_lower or keyword in title_lower:
                    return page_type
        
        return PageType.UNKNOWN
    
    async def _extract_page_elements(self, page_context) -> Dict[str, ElementInfo]:
        """提取页面元素"""
        elements = {}
        
        if not page_context:
            return elements
        
        # 遍历元素类型，查找对应元素
        for element_type, selectors in self.element_classifiers.items():
            for selector in selectors:
                try:
                    # 查找元素
                    # element_handles = await page_context.query_selector_all(selector)
                    # 模拟找到元素
                    element_handles = [f"mock_element_{selector}"]
                    
                    for i, handle in enumerate(element_handles):
                        element_id = f"{element_type.value}_{i}"
                        
                        # 获取元素信息
                        # text = await handle.text_content()
                        # attributes = await handle.get_attributes()
                        text = f"Mock text for {selector}"
                        attributes = {"class": "mock-class"}
                        
                        element_info = ElementInfo(
                            id=element_id,
                            type=element_type,
                            selectors=[selector],
                            text=text,
                            attributes=attributes,
                            last_verified=datetime.now()
                        )
                        
                        elements[element_id] = element_info
                        
                except Exception as e:
                    # 元素未找到或其他错误
                    continue
        
        return elements
    
    def _extract_links(self, page_info: PageInfo, base_url: str) -> List[str]:
        """从页面信息中提取链接"""
        links = []
        
        # 从元素中提取链接
        for element in page_info.elements.values():
            if element.type == ElementType.LINK:
                href = element.attributes.get('href')
                if href:
                    absolute_url = urljoin(base_url, href)
                    links.append(absolute_url)
        
        # 模拟一些链接
        parsed_url = urlparse(base_url)
        mock_links = [
            f"{parsed_url.scheme}://{parsed_url.netloc}/products",
            f"{parsed_url.scheme}://{parsed_url.netloc}/about",
            f"{parsed_url.scheme}://{parsed_url.netloc}/contact"
        ]
        links.extend(mock_links)
        
        return list(set(links))  # 去重
    
    def _should_exclude_url(self, url: str, exclude_patterns: List[str]) -> bool:
        """检查URL是否应该被排除"""
        for pattern in exclude_patterns:
            if pattern in url:
                return True
        return False
    
    async def _perform_interactions(self, page_info: PageInfo, page_context):
        """执行页面交互"""
        # 尝试点击按钮、悬停等操作
        for element in page_info.elements.values():
            if element.type in [ElementType.BUTTON, ElementType.LINK]:
                try:
                    # await page_context.hover(element.selectors[0])
                    # await page_context.click(element.selectors[0])
                    pass
                except Exception:
                    continue
    
    async def _find_target_elements(self, element_type: str, page_info: PageInfo, page_context):
        """查找目标元素"""
        target_type = ElementType(element_type)
        selectors = self.element_classifiers.get(target_type, [])
        
        for selector in selectors:
            try:
                # elements = await page_context.query_selector_all(selector)
                # 处理找到的元素
                pass
            except Exception:
                continue
    
    def _increment_version(self, version: str) -> str:
        """递增版本号"""
        parts = version.split('.')
        if len(parts) == 3:
            parts[2] = str(int(parts[2]) + 1)
            return '.'.join(parts)
        return version
    
    def get_site_model(self, domain: str) -> Optional[SiteModel]:
        """获取站点模型"""
        model = self.site_models.get(domain)
        if model and self._is_model_expired(model):
            # 模型已过期
            return None
        return model
    
    def _is_model_expired(self, model: SiteModel) -> bool:
        """检查模型是否过期"""
        return datetime.now() - model.last_updated > model.ttl
    
    def update_element_confidence(self, domain: str, element_id: str, success: bool):
        """更新元素选择器的可靠性"""
        model = self.site_models.get(domain)
        if not model:
            return
        
        # 在所有页面中查找元素
        for page in model.pages.values():
            if element_id in page.elements:
                element = page.elements[element_id]
                if success:
                    element.confidence = min(element.confidence + 0.1, 1.0)
                else:
                    element.confidence = max(element.confidence - 0.2, 0.1)
                element.last_verified = datetime.now()
                break
    
    def find_element_by_purpose(self, domain: str, purpose: str) -> Optional[ElementInfo]:
        """根据用途查找元素"""
        model = self.site_models.get(domain)
        if not model:
            return None
        
        # 在全局元素中查找
        for element in model.global_elements.values():
            if element.purpose and purpose.lower() in element.purpose.lower():
                return element
        
        # 在页面元素中查找
        for page in model.pages.values():
            for element in page.elements.values():
                if element.purpose and purpose.lower() in element.purpose.lower():
                    return element
        
        return None
    
    def get_navigation_path(self, domain: str, from_page: str, to_page: str) -> List[NavigationEdge]:
        """获取导航路径"""
        model = self.site_models.get(domain)
        if not model:
            return []
        
        # 简单实现：直接查找边
        path = []
        for edge in model.navigation_graph:
            if edge.from_page == from_page and edge.to_page == to_page:
                path.append(edge)
                break
        
        return path
    
    def export_model(self, domain: str) -> Optional[Dict[str, Any]]:
        """导出站点模型"""
        model = self.site_models.get(domain)
        if not model:
            return None
        
        return {
            "domain": model.domain,
            "version": model.version,
            "pages": {
                url: {
                    "title": page.title,
                    "type": page.type.value,
                    "description": page.description,
                    "elements": {
                        elem_id: {
                            "type": elem.type.value,
                            "selectors": elem.selectors,
                            "text": elem.text,
                            "purpose": elem.purpose,
                            "confidence": elem.confidence
                        }
                        for elem_id, elem in page.elements.items()
                    }
                }
                for url, page in model.pages.items()
            },
            "navigation_graph": [
                {
                    "from": edge.from_page,
                    "to": edge.to_page,
                    "trigger": edge.trigger_element,
                    "action": edge.action_type,
                    "success_rate": edge.success_rate
                }
                for edge in model.navigation_graph
            ],
            "metadata": model.metadata,
            "created_at": model.created_at.isoformat(),
            "last_updated": model.last_updated.isoformat()
        }
    
    def import_model(self, model_data: Dict[str, Any]) -> bool:
        """导入站点模型"""
        try:
            domain = model_data["domain"]
            
            # 重建模型
            model = SiteModel(
                domain=domain,
                version=model_data["version"],
                metadata=model_data.get("metadata", {}),
                created_at=datetime.fromisoformat(model_data["created_at"]),
                last_updated=datetime.fromisoformat(model_data["last_updated"])
            )
            
            # 重建页面
            for url, page_data in model_data["pages"].items():
                elements = {}
                for elem_id, elem_data in page_data["elements"].items():
                    elements[elem_id] = ElementInfo(
                        id=elem_id,
                        type=ElementType(elem_data["type"]),
                        selectors=elem_data["selectors"],
                        text=elem_data.get("text"),
                        purpose=elem_data.get("purpose"),
                        confidence=elem_data.get("confidence", 1.0)
                    )
                
                page = PageInfo(
                    url=url,
                    title=page_data["title"],
                    type=PageType(page_data["type"]),
                    description=page_data.get("description"),
                    elements=elements
                )
                model.pages[url] = page
            
            # 重建导航图
            for edge_data in model_data["navigation_graph"]:
                edge = NavigationEdge(
                    from_page=edge_data["from"],
                    to_page=edge_data["to"],
                    trigger_element=edge_data["trigger"],
                    action_type=edge_data["action"],
                    success_rate=edge_data.get("success_rate", 1.0)
                )
                model.navigation_graph.append(edge)
            
            self.site_models[domain] = model
            return True
            
        except Exception as e:
            print(f"Failed to import model: {str(e)}")
            return False


# 示例使用
if __name__ == "__main__":
    import asyncio
    
    async def main():
        explorer = SiteExplorer()
        
        # 创建探索任务
        task = ExplorationTask(
            id="task_001",
            domain="example.com",
            start_url="https://example.com",
            strategy=ExplorationStrategy.BREADTH_FIRST,
            max_depth=2,
            max_pages=10
        )
        
        # 执行探索
        model = await explorer.explore_site(task)
        
        # 导出模型
        exported = explorer.export_model("example.com")
        if exported:
            print(f"Exported model for {exported['domain']} with {len(exported['pages'])} pages")
        
        # 查找搜索功能
        search_element = explorer.find_element_by_purpose("example.com", "搜索")
        if search_element:
            print(f"Found search element: {search_element.selectors}")
    
    def set_mcp_manager(self, mcp_manager):
        """设置 MCP 管理器"""
        self.mcp_manager = mcp_manager
    
    async def enable_browser_extension_mode(self) -> bool:
        """启用浏览器扩展模式
        
        Returns:
            是否成功启用
        """
        if not self.mcp_manager:
            return False
            
        try:
            # 检查 MCP 是否已初始化
            if not self.mcp_manager.is_initialized:
                await self.mcp_manager.initialize()
                
            # 获取可用的浏览器标签页
            tabs_info = await self._get_browser_tabs()
            if tabs_info:
                self._browser_extension_mode = True
                self._active_browser_tabs = tabs_info
                return True
                
            return False
            
        except Exception as e:
            print(f"Failed to enable browser extension mode: {e}")
            return False
    
    async def _get_browser_tabs(self) -> Dict[str, Any]:
        """获取浏览器标签页信息"""
        if not self.mcp_manager or not self.mcp_manager.agent:
            return {}
            
        try:
            # 通过 MCP 获取浏览器标签页
            result = await self.mcp_manager.execute_command(
                "List all available browser tabs and their URLs"
            )
            
            # 解析结果（这里需要根据实际 MCP 返回格式调整）
            # 假设返回格式包含标签页信息
            return {"tabs": result}
            
        except Exception as e:
            print(f"Error getting browser tabs: {e}")
            return {}
    
    async def explore_with_extension(self, domain: str, target_tab_url: str = None) -> Optional[SiteModel]:
        """使用浏览器扩展模式探索站点
        
        Args:
            domain: 目标域名
            target_tab_url: 目标标签页URL（如果为空则使用当前活跃标签页）
            
        Returns:
            站点模型
        """
        if not self._browser_extension_mode or not self.mcp_manager:
            raise ValueError("Browser extension mode not enabled")
            
        try:
            # 如果指定了目标URL，导航到该页面
            if target_tab_url:
                await self.mcp_manager.execute_command(
                    f"Navigate to {target_tab_url}"
                )
            
            # 获取当前页面信息
            page_info = await self._analyze_current_page()
            
            # 创建或更新站点模型
            if domain not in self.site_models:
                self.site_models[domain] = SiteModel(
                    domain=domain,
                    version="1.0"
                )
            
            model = self.site_models[domain]
            
            # 添加页面信息到模型
            if page_info:
                model.pages[page_info["url"]] = PageInfo(
                    url=page_info["url"],
                    title=page_info.get("title", ""),
                    type=self._classify_page_type(page_info["url"], page_info.get("title", "")),
                    elements=page_info.get("elements", {}),
                    metadata=page_info.get("metadata", {})
                )
                
                model.last_updated = datetime.now()
            
            return model
            
        except Exception as e:
            print(f"Error exploring with extension: {e}")
            return None
    
    async def _analyze_current_page(self) -> Optional[Dict[str, Any]]:
        """分析当前页面
        
        Returns:
            页面信息字典
        """
        if not self.mcp_manager:
            return None
            
        try:
            # 获取页面基本信息
            page_info_cmd = """
            Get the current page information including:
            - URL
            - Title
            - All interactive elements (buttons, links, forms)
            - Page structure and navigation elements
            """
            
            result = await self.mcp_manager.execute_command(page_info_cmd)
            
            # 解析结果（需要根据实际 MCP 返回格式调整）
            return {
                "url": "current_page_url",  # 从结果中提取
                "title": "current_page_title",  # 从结果中提取
                "elements": {},  # 从结果中提取元素列表
                "metadata": {"raw_result": result}
            }
            
        except Exception as e:
            print(f"Error analyzing current page: {e}")
            return None
    
    async def interact_with_element(self, element_selector: str, action: str = "click") -> bool:
        """与页面元素交互
        
        Args:
            element_selector: 元素选择器
            action: 交互动作（click, type, hover等）
            
        Returns:
            是否成功
        """
        if not self._browser_extension_mode or not self.mcp_manager:
            return False
            
        try:
            command = f"{action.capitalize()} on element: {element_selector}"
            await self.mcp_manager.execute_command(command)
            return True
            
        except Exception as e:
            print(f"Error interacting with element: {e}")
            return False
    
    async def take_screenshot(self, filename: str = None) -> Optional[str]:
        """截取当前页面截图
        
        Args:
            filename: 截图文件名
            
        Returns:
            截图文件路径
        """
        if not self._browser_extension_mode or not self.mcp_manager:
            return None
            
        try:
            screenshot_cmd = f"Take a screenshot"
            if filename:
                screenshot_cmd += f" and save as {filename}"
                
            result = await self.mcp_manager.execute_command(screenshot_cmd)
            return result  # 假设返回文件路径
            
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return None
    
    async def get_session_state(self) -> Dict[str, Any]:
        """获取当前浏览器会话状态
        
        Returns:
            会话状态信息
        """
        if not self._browser_extension_mode:
            return {"extension_mode": False}
            
        return {
            "extension_mode": True,
            "active_tabs": self._active_browser_tabs,
            "mcp_initialized": self.mcp_manager.is_initialized if self.mcp_manager else False
        }
    
    def disable_browser_extension_mode(self):
        """禁用浏览器扩展模式"""
        self._browser_extension_mode = False
        self._active_browser_tabs = {}
    
    # asyncio.run(main())