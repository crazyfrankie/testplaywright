"""
Playwright 浏览器内容提取器

使用 Playwright 自动化浏览器提取网页内容
适用于需要 JavaScript 渲染或有反爬虫的网站
"""

from typing import Optional
from contextlib import contextmanager
from playwright.sync_api import (
    sync_playwright, 
    Page, 
    TimeoutError as PlaywrightTimeout,
    Error as PlaywrightError
)
from .base import ContentExtractor, ExtractedContent
import re


class BrowserExtractor(ContentExtractor):
    """
    基于 Playwright 的浏览器内容提取器
    
    优点：
    - 支持 JavaScript 渲染
    - 可以处理复杂的反爬虫
    - 完全控制浏览器行为
    - 不依赖外部服务
    
    缺点：
    - 速度较慢（需要启动浏览器）
    - 资源占用高
    """

    def __init__(
        self, 
        timeout: int = 30, 
        headless: bool = True, 
        block_resources: bool = True, 
        include_images: bool = False,
        user_agent: Optional[str] = None
    ):
        """
        初始化 Playwright 提取器
        
        Args:
            timeout: 页面加载超时时间（秒）
            headless: 是否无头模式运行
            block_resources: 是否阻止加载图片、视频等资源（默认 True，提高速度）
            include_images: 是否包含图片链接（默认 False，只提取纯文本）
            user_agent: 自定义 User-Agent（可选）
        """
        super().__init__(timeout)
        self.headless = headless
        self.block_resources = block_resources
        self.include_images = include_images
        self.user_agent = user_agent
        self._playwright = None
        self._browser = None
    
    def __enter__(self):
        """进入 context manager"""
        self._start_browser()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出 context manager，自动清理资源"""
        self._close_browser()
        return False  # 不抑制异常
    
    def _start_browser(self):
        """启动浏览器"""
        if self._browser is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=self.headless,
                args=['--disable-blink-features=AutomationControlled']  # 反检测
            )
    
    def _close_browser(self):
        """关闭浏览器并清理资源"""
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            finally:
                self._browser = None
        
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            finally:
                self._playwright = None
    
    @contextmanager
    def _get_page(self):
        """
        获取页面的 context manager
        自动管理浏览器和页面的生命周期
        """
        should_close_browser = False
        if self._browser is None:
            self._start_browser()
            should_close_browser = True
        
        # 创建浏览器上下文（更好的隔离性）
        context = self._browser.new_context(
            user_agent=self.user_agent,
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
        )
        
        # 创建页面
        page = context.new_page()
        page.set_default_timeout(self.timeout * 1000)
        
        try:
            yield page
        finally:
            # 清理资源
            try:
                page.close()
            except Exception:
                pass
            
            try:
                context.close()
            except Exception:
                pass
            
            if should_close_browser:
                self._close_browser()
    
    def extract(self, url: str) -> ExtractedContent:
        """
        提取网页内容
        
        Args:
            url: 目标网址
            
        Returns:
            ExtractedContent: 提取的内容对象
        """
        try:
            with self._get_page() as page:
                # 如果需要阻止资源加载，设置路由拦截
                if self.block_resources:
                    self._setup_resource_blocking(page)
                
                # 访问页面（使用 domcontentloaded 而不是 load，更快）
                page.goto(url, wait_until="domcontentloaded")
                
                # 移除广告和弹窗元素
                self._remove_unwanted_elements(page)
                
                # 等待主要内容加载（但不等待所有网络请求）
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except PlaywrightTimeout:
                    pass  # 超时继续，不强制等待
                
                # 提取内容
                return self._extract_content_from_page(page, url)
        
        except PlaywrightTimeout:
            return self._create_error_result(url, f"页面加载超时（{self.timeout}秒）")
        
        except PlaywrightError as e:
            return self._create_error_result(url, f"浏览器错误: {str(e)}")
        
        except Exception as e:
            return self._create_error_result(url, f"提取失败: {str(e)}")
    
    def _setup_resource_blocking(self, page: Page):
        """
        设置资源阻止，只阻止广告和弹窗相关的资源，保留文章图片
        
        Args:
            page: Playwright 页面对象
        """
        # 需要阻止的资源类型（保留文章图片）
        BLOCKED_TYPES = {'media', 'font'}  # 只阻止视频和字体
        
        # 广告和弹窗相关的 URL 关键词
        AD_KEYWORDS = {
            '/ad/', '/ads/', '/advertisement/', '/banner/', '/popup/',
            'doubleclick', 'google-analytics', 'googletagmanager',
            'googlesyndication', 'adservice', 'adsystem',
            'ad.doubleclick', 'pagead', 'adserver',
        }
        
        # 统计和追踪相关的关键词
        TRACKING_KEYWORDS = {
            'analytics', 'tracking', 'tracker', 'pixel',
            'beacon', 'telemetry', 'metrics',
        }
        
        # 广告图片的常见特征（文件名或路径）
        AD_IMAGE_PATTERNS = {
            'ad_', 'ads_', 'banner_', 'popup_',
            '_ad.', '_ads.', '_banner.', '_popup.',
            '/ad.', '/ads.', '/banner.', '/popup.',
        }
        
        def handle_route(route):
            request = route.request
            url_lower = request.url.lower()
            
            # 1. 阻止非图片的媒体资源（视频、字体等）
            if request.resource_type in BLOCKED_TYPES:
                return route.abort()
            
            # 2. 对于图片资源，只阻止广告图片
            if request.resource_type == 'image':
                # 检查是否是广告图片
                is_ad_image = (
                    any(keyword in url_lower for keyword in AD_KEYWORDS) or
                    any(pattern in url_lower for pattern in AD_IMAGE_PATTERNS)
                )
                
                if is_ad_image:
                    return route.abort()  # 阻止广告图片
                else:
                    return route.continue_()  # 允许文章图片
            
            # 3. 阻止广告和追踪相关的请求
            if any(keyword in url_lower for keyword in AD_KEYWORDS | TRACKING_KEYWORDS):
                return route.abort()
            
            # 4. 阻止样式表（可选，提高速度）
            if request.resource_type == 'stylesheet':
                return route.abort()
            
            # 其他请求正常通过
            route.continue_()
        
        # 设置路由拦截
        page.route('**/*', handle_route)
    
    def _remove_unwanted_elements(self, page: Page):
        """
        移除页面中的广告、弹窗等不需要的元素（保留文章图片）
        
        Args:
            page: Playwright 页面对象
        """
        # 常见的广告和弹窗选择器（更精确，避免误删文章图片）
        UNWANTED_SELECTORS = [
            # 广告容器
            '.ad', '.ads', '.advertisement', '.ad-container',
            '.google-ad', '.adsense', '.adsbygoogle',
            '#ad', '#ads', '#advertisement',
            '[class*="ad-"]', '[class*="ads-"]',
            '[id*="ad-"]', '[id*="ads-"]',
            
            # 弹窗和遮罩
            '.popup', '.modal', '.overlay', '.mask',
            '.dialog', '.lightbox', '.fancybox',
            '[class*="popup"]', '[class*="modal"]',
            
            # Banner 广告
            '.banner', '.top-banner', '.bottom-banner',
            '.side-banner', '[class*="banner"]',
            
            # 广告 iframe
            'iframe[src*="ad"]', 'iframe[src*="ads"]',
            'iframe[src*="doubleclick"]', 'iframe[src*="googlesyndication"]',
        ]
        
        # 批量移除所有匹配的元素（一次性执行，更高效）
        selectors_str = ', '.join(UNWANTED_SELECTORS)
        try:
            page.evaluate(f'''
                // 移除广告和弹窗元素
                document.querySelectorAll("{selectors_str}").forEach(el => {{
                    el.remove();
                }});
                
                // 移除固定定位的遮罩层（通常是弹窗背景）
                document.querySelectorAll('[style*="position: fixed"]').forEach(el => {{
                    const zIndex = window.getComputedStyle(el).zIndex;
                    // 只移除高 z-index 的元素（通常是弹窗）
                    if (zIndex && parseInt(zIndex) > 1000) {{
                        const className = el.className.toLowerCase();
                        const id = el.id.toLowerCase();
                        // 检查是否是广告或弹窗相关
                        if (className.includes('ad') || className.includes('popup') || 
                            className.includes('modal') || className.includes('overlay') ||
                            id.includes('ad') || id.includes('popup') || 
                            id.includes('modal') || id.includes('overlay')) {{
                            el.remove();
                        }}
                    }}
                }});
            ''')
        except Exception:
            pass  # 忽略错误
    
    def _extract_content_from_page(self, page: Page, url: str) -> ExtractedContent:
        """
        从页面提取内容
        
        Args:
            page: Playwright 页面对象
            url: 原始 URL
            
        Returns:
            ExtractedContent: 提取的内容对象
        """
        try:
            # 提取标题
            title = self._extract_title(page)
            
            # 提取正文
            content = self._extract_main_content(page)
            
            # 清理内容（移除图片链接等）
            if not self.include_images:
                content = self._remove_images_from_content(content)
            
            # 提取作者
            author = self._extract_author(page)
            
            # 提取发布日期
            publish_date = self._extract_publish_date(page)
            
            # 提取平台信息
            platform = self._extract_platform_from_url(url)
            platform_logo = self._get_platform_logo(url)
            
            return ExtractedContent(
                url=url,
                title=title,
                content=content,
                platform=platform,
                platform_logo=platform_logo,
                author=author,
                publish_date=publish_date,
                success=True
            )
        
        except Exception as e:
            return self._create_error_result(url, f"内容解析失败: {str(e)}")
    
    def _extract_title(self, page: Page) -> str:
        """提取标题"""
        # 尝试多种选择器（按优先级排序）
        TITLE_SELECTORS = [
            ('meta[property="og:title"]', 'content'),
            ('meta[name="twitter:title"]', 'content'),
            ('h1', 'text'),
            ('article h1', 'text'),
            ('.article-title', 'text'),
            ('.post-title', 'text'),
            ('.title', 'text'),
        ]
        
        for selector, attr_type in TITLE_SELECTORS:
            try:
                element = page.query_selector(selector)
                if element:
                    if attr_type == 'content':
                        title = element.get_attribute('content')
                    else:
                        title = element.inner_text()
                    
                    if title and title.strip():
                        return title.strip()
            except Exception:
                continue
        
        # 最后尝试 <title> 标签
        try:
            title = page.title()
            if title:
                return title
        except Exception:
            pass
        
        return "无标题"
    
    def _extract_main_content(self, page: Page) -> str:
        """提取正文内容（包含图片）"""
        # 尝试多种常见的文章容器选择器（按优先级排序）
        CONTENT_SELECTORS = [
            'article',
            '.article-content',
            '.post-content',
            '.entry-content',
            '.content',
            '.main-content',
            '#article-content',
            '#content',
            'main',
        ]
        
        MIN_CONTENT_LENGTH = 100  # 最小内容长度
        
        for selector in CONTENT_SELECTORS:
            try:
                element = page.query_selector(selector)
                if element:
                    # 如果需要包含图片，提取 HTML 并转换为 Markdown
                    if self.include_images:
                        html = element.inner_html()
                        markdown = self._html_to_markdown_with_images(page, html)
                        if markdown and len(markdown) >= MIN_CONTENT_LENGTH:
                            return markdown
                    else:
                        # 只提取文本
                        text = element.inner_text()
                        if text and len(text) >= MIN_CONTENT_LENGTH:
                            text = self._clean_text(text)
                            return self._convert_to_markdown(text)
            except Exception:
                continue
        
        # 如果没有找到，尝试获取 body 的内容
        try:
            body = page.query_selector('body')
            if body:
                if self.include_images:
                    html = body.inner_html()
                    return self._html_to_markdown_with_images(page, html)
                else:
                    text = body.inner_text()
                    if text:
                        return self._clean_text(text)
        except Exception:
            pass
        
        return "无法提取内容"
    
    def _extract_author(self, page: Page) -> Optional[str]:
        """提取作者"""
        AUTHOR_SELECTORS = [
            ('meta[name="author"]', 'content'),
            ('meta[property="article:author"]', 'content'),
            ('.author', 'text'),
            ('.author-name', 'text'),
            ('.post-author', 'text'),
            ('[rel="author"]', 'text'),
        ]
        
        return self._extract_by_selectors(page, AUTHOR_SELECTORS)
    
    def _extract_publish_date(self, page: Page) -> Optional[str]:
        """提取发布日期"""
        DATE_SELECTORS = [
            ('meta[property="article:published_time"]', 'content'),
            ('meta[name="publish_date"]', 'content'),
            ('time', 'datetime'),
            ('time', 'text'),
            ('.publish-date', 'text'),
            ('.post-date', 'text'),
            ('.entry-date', 'text'),
        ]
        
        return self._extract_by_selectors(page, DATE_SELECTORS)
    
    def _extract_by_selectors(
        self, 
        page: Page, 
        selectors: list[tuple[str, str]]
    ) -> Optional[str]:
        """
        通用的选择器提取方法
        
        Args:
            page: Playwright 页面对象
            selectors: 选择器列表，格式为 [(selector, attr_type), ...]
                      attr_type 可以是 'content', 'text', 'datetime' 等
        
        Returns:
            提取的文本，如果没有找到则返回 None
        """
        for selector, attr_type in selectors:
            try:
                element = page.query_selector(selector)
                if not element:
                    continue
                
                # 根据属性类型提取内容
                if attr_type == 'content':
                    value = element.get_attribute('content')
                elif attr_type == 'datetime':
                    value = element.get_attribute('datetime')
                elif attr_type == 'text':
                    value = element.inner_text()
                else:
                    value = element.get_attribute(attr_type)
                
                if value and value.strip():
                    return value.strip()
            
            except Exception:
                continue
        
        return None
    
    def _remove_images_from_content(self, content: str) -> str:
        """
        从内容中移除图片链接
        
        Args:
            content: 原始内容
            
        Returns:
            str: 移除图片后的内容
        """
        # 移除 Markdown 图片语法
        content = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', '', content)
        
        # 移除 HTML img 标签
        content = re.sub(r'<img[^>]*>', '', content)
        
        # 移除单独的图片 URL
        content = re.sub(
            r'^https?://[^\s]+\.(jpg|jpeg|png|gif|webp|svg)(\?[^\s]*)?$', 
            '', 
            content, 
            flags=re.MULTILINE | re.IGNORECASE
        )
        
        return content
    
    def _clean_text(self, text: str) -> str:
        """
        清理文本，移除多余的空白字符
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理后的文本
        """
        # 移除多余的空行（保留最多一个空行）
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        
        # 移除行内多余的空格
        text = re.sub(r' +', ' ', text)
        
        # 移除行首行尾空格
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text.strip()
    
    def _convert_to_markdown(self, text: str) -> str:
        """
        将文本转换为简单的 Markdown 格式
        
        Args:
            text: 原始文本
            
        Returns:
            str: Markdown 格式的文本
        """
        # 按段落分隔
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        # 用空行连接段落
        return '\n\n'.join(paragraphs)
    
    def _html_to_markdown_with_images(self, page: Page, html: str) -> str:
        """
        将 HTML 转换为 Markdown 格式（保留图片）
        
        Args:
            page: Playwright 页面对象
            html: HTML 内容
            
        Returns:
            str: Markdown 格式的内容（包含图片）
        """
        try:
            # 使用 JavaScript 在浏览器中转换（更准确）
            markdown = page.evaluate('''
                (html) => {
                    const div = document.createElement('div');
                    div.innerHTML = html;
                    
                    let result = [];
                    
                    // 递归处理节点
                    function processNode(node) {
                        if (node.nodeType === Node.TEXT_NODE) {
                            const text = node.textContent.trim();
                            if (text) result.push(text);
                        } else if (node.nodeType === Node.ELEMENT_NODE) {
                            const tagName = node.tagName.toLowerCase();
                            
                            // 处理图片
                            if (tagName === 'img') {
                                const src = node.getAttribute('src');
                                const alt = node.getAttribute('alt') || '图片';
                                if (src) {
                                    // 转换为绝对 URL
                                    const absoluteSrc = new URL(src, window.location.href).href;
                                    result.push(`\n\n![${alt}](${absoluteSrc})\n\n`);
                                }
                            }
                            // 处理标题
                            else if (/^h[1-6]$/.test(tagName)) {
                                const level = parseInt(tagName[1]);
                                const text = node.textContent.trim();
                                if (text) {
                                    result.push(`\n\n${'#'.repeat(level)} ${text}\n\n`);
                                }
                            }
                            // 处理段落
                            else if (tagName === 'p') {
                                node.childNodes.forEach(child => processNode(child));
                                result.push('\n\n');
                            }
                            // 处理换行
                            else if (tagName === 'br') {
                                result.push('\n');
                            }
                            // 处理链接
                            else if (tagName === 'a') {
                                const href = node.getAttribute('href');
                                const text = node.textContent.trim();
                                if (href && text) {
                                    const absoluteHref = new URL(href, window.location.href).href;
                                    result.push(`[${text}](${absoluteHref})`);
                                } else if (text) {
                                    result.push(text);
                                }
                            }
                            // 处理粗体
                            else if (tagName === 'strong' || tagName === 'b') {
                                const text = node.textContent.trim();
                                if (text) result.push(`**${text}**`);
                            }
                            // 处理斜体
                            else if (tagName === 'em' || tagName === 'i') {
                                const text = node.textContent.trim();
                                if (text) result.push(`*${text}*`);
                            }
                            // 处理代码
                            else if (tagName === 'code') {
                                const text = node.textContent.trim();
                                if (text) result.push(`\`${text}\``);
                            }
                            // 处理列表
                            else if (tagName === 'ul' || tagName === 'ol') {
                                result.push('\n');
                                const items = node.querySelectorAll('li');
                                items.forEach((item, index) => {
                                    const prefix = tagName === 'ul' ? '- ' : `${index + 1}. `;
                                    result.push(`${prefix}${item.textContent.trim()}\n`);
                                });
                                result.push('\n');
                            }
                            // 其他元素递归处理子节点
                            else {
                                node.childNodes.forEach(child => processNode(child));
                            }
                        }
                    }
                    
                    div.childNodes.forEach(node => processNode(node));
                    
                    // 清理多余的空行
                    return result.join('').replace(/\n{3,}/g, '\n\n').trim();
                }
            ''', html)
            
            return markdown if markdown else "无法提取内容"
        
        except Exception as e:
            # 如果 JavaScript 转换失败，降级为纯文本
            return self._clean_text(html)
