"""
Jina Reader API 内容提取器

使用 Jina AI 的 Reader API 提取网页内容
官方文档: https://jina.ai/reader
"""

import requests
import os
from typing import Optional
from .base import ContentExtractor, ExtractedContent


class JinaExtractor(ContentExtractor):
    """
    基于 Jina Reader API 的内容提取器
    
    优点：
    - 免费使用（每天 1000 次请求）
    - 支持几乎所有网站
    - 自动处理反爬虫
    - 返回 Markdown 格式
    - 无需浏览器
    
    缺点：
    - 依赖外部服务
    - 需要网络连接
    """
    
    def __init__(self, timeout: int = 30, api_key: Optional[str] = None, 
                 include_images: bool = False, max_retries: int = 2):
        """
        初始化 Jina 提取器
        
        Args:
            timeout: 请求超时时间（秒）
            api_key: Jina API Key（可选，会自动从环境变量 JINA_API_KEY 读取）
            include_images: 是否包含图片链接（默认 False，只提取纯文本）
            max_retries: 最大重试次数（默认 2 次）
        """
        super().__init__(timeout)
        self.base_url = "https://r.jina.ai/"

        self.api_key = api_key or os.getenv('JINA_API_KEY')
        
        self.include_images = include_images
        self.max_retries = max_retries
    
    def extract(self, url: str) -> ExtractedContent:
        """
        提取网页内容（带重试机制）
        
        Args:
            url: 目标网址
            
        Returns:
            ExtractedContent: 提取的内容对象
        """
        last_error = None
        
        # 重试机制
        for attempt in range(self.max_retries + 1):
            try:
                result = self._do_extract(url)
                if result.success:
                    return result
                last_error = result.error
            except Exception as e:
                last_error = str(e)
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < self.max_retries:
                import time
                time.sleep(1)  # 等待 1 秒后重试
        
        # 所有重试都失败
        return self._create_error_result(url, f"重试 {self.max_retries} 次后仍失败: {last_error}")
    
    def _do_extract(self, url: str) -> ExtractedContent:
        """
        执行实际的内容提取
        
        Args:
            url: 目标网址
            
        Returns:
            ExtractedContent: 提取的内容对象
        """
        try:
            # 构建请求头
            headers = {
                "X-Return-Format": "markdown",  # 返回 Markdown 格式
                "X-Timeout": str(self.timeout),  # 设置超时
                "X-With-Generated-Alt": "false",  # 不生成图片 alt 文本
            }
            
            # 根据配置决定是否包含图片
            if self.include_images:
                headers["X-With-Images-Summary"] = "true"  # 包含图片
            else:
                headers["X-With-Images-Summary"] = "false"  # 不包含图片
            
            # 移除常见的广告、弹窗和广告图片元素（但保留文章图片）
            # 使用更精确的选择器，避免误删文章内容
            headers["X-Remove-Selector"] = (
                ".ad,.ads,.advertisement,.ad-container,.google-ad,.adsense,.adsbygoogle,"
                ".popup,.modal,.overlay,.mask,.dialog,"
                ".banner,.top-banner,.bottom-banner,.side-banner,"
                "#ad,#ads,#advertisement,"
                "[class*='ad-'],[class*='ads-'],[id*='ad-'],[id*='ads-'],"
                "iframe[src*='ad'],iframe[src*='ads'],iframe[src*='doubleclick']"
            )
            
            # 如果有 API Key，添加到请求头
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            # 发送请求
            response = requests.get(
                f"{self.base_url}{url}",
                headers=headers,
                timeout=self.timeout
            )
            
            # 检查响应状态
            if response.status_code == 200:
                content = response.text
                
                # 清理内容（移除图片链接等）
                if not self.include_images:
                    content = self._remove_images_from_markdown(content)
                
                # 清理多余的空行和格式
                content = self._clean_content(content)
                
                # 提取标题（通常是第一行的 # 标题）
                title = self._extract_title(content)
                
                # 提取平台信息
                platform = self._extract_platform_from_url(url)
                platform_logo = self._get_platform_logo(url)
                
                # 尝试从响应头获取额外信息
                author = response.headers.get('X-Author')
                publish_date = response.headers.get('X-Publish-Date')
                
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
            
            elif response.status_code == 429:
                # 请求过多
                return self._create_error_result(url, "请求频率过高，请稍后再试")
            
            elif response.status_code == 404:
                return self._create_error_result(url, "页面不存在")
            
            else:
                return self._create_error_result(
                    url, 
                    f"HTTP {response.status_code}: {response.text[:100]}"
                )
        
        except requests.exceptions.Timeout:
            return self._create_error_result(url, f"请求超时（{self.timeout}秒）")
        
        except requests.exceptions.ConnectionError:
            return self._create_error_result(url, "网络连接失败")
        
        except Exception as e:
            return self._create_error_result(url, f"未知错误: {str(e)}")
    
    def _extract_title(self, content: str) -> str:
        """
        从 Markdown 内容中提取标题
        
        Args:
            content: Markdown 内容
            
        Returns:
            str: 标题
        """
        if not content:
            return ""
        
        lines = content.split('\n')
        
        # 查找第一个 # 标题
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                # 移除 # 符号和空格
                title = line.lstrip('#').strip()
                if title:
                    return title
        
        # 如果没有找到标题，返回第一行非空内容
        for line in lines:
            line = line.strip()
            if line:
                return line[:100]  # 最多取前 100 个字符
        
        return "无标题"
    
    def _remove_images_from_markdown(self, content: str) -> str:
        """
        从 Markdown 内容中移除广告图片，保留文章图片
        
        Args:
            content: Markdown 内容
            
        Returns:
            str: 移除广告图片后的内容
        """
        import re
        
        # 广告图片的常见特征（URL 或 alt 文本中包含这些关键词）
        AD_KEYWORDS = [
            'ad', 'ads', 'advertisement', 'banner', 'popup',
            'doubleclick', 'googlesyndication', 'adservice',
            'sponsor', 'promo', 'promotion'
        ]
        
        # 查找所有 Markdown 图片
        def filter_image(match):
            alt_text = match.group(1).lower()
            url = match.group(2).lower()
            
            # 检查是否是广告图片
            is_ad = any(keyword in alt_text or keyword in url for keyword in AD_KEYWORDS)
            
            if is_ad:
                return ''  # 移除广告图片
            else:
                return match.group(0)  # 保留文章图片
        
        # 处理 Markdown 图片语法: ![alt](url)
        content = re.sub(r'!\[([^\]]*)\]\(([^\)]+)\)', filter_image, content)
        
        # 移除 HTML img 标签中的广告图片
        def filter_html_image(match):
            img_tag = match.group(0).lower()
            is_ad = any(keyword in img_tag for keyword in AD_KEYWORDS)
            return '' if is_ad else match.group(0)
        
        content = re.sub(r'<img[^>]*>', filter_html_image, content, flags=re.IGNORECASE)
        
        return content
    
    def _clean_content(self, content: str) -> str:
        """
        清理内容格式
        
        Args:
            content: 原始内容
            
        Returns:
            str: 清理后的内容
        """
        import re
        
        # 移除多余的空行（3个以上连续换行变成2个）
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 移除行首行尾的空格
        lines = [line.rstrip() for line in content.split('\n')]
        content = '\n'.join(lines)
        
        # 移除开头和结尾的空行
        content = content.strip()
        
        return content
    
    def extract_with_images(self, url: str) -> ExtractedContent:
        """
        提取内容并保留图片链接
        
        Args:
            url: 目标网址
            
        Returns:
            ExtractedContent: 提取的内容对象
        """
        # 修改请求头，保留图片
        headers = {
            "X-Return-Format": "markdown",
            "X-With-Images-Summary": "true",  # 包含图片摘要
            "X-Timeout": str(self.timeout),
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            response = requests.get(
                f"{self.base_url}{url}",
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                content = response.text
                title = self._extract_title(content)
                
                return ExtractedContent(
                    url=url,
                    title=title,
                    content=content,
                    platform=self._extract_platform_from_url(url),
                    platform_logo=self._get_platform_logo(url),
                    success=True
                )
            else:
                return self._create_error_result(url, f"HTTP {response.status_code}")
        
        except Exception as e:
            return self._create_error_result(url, str(e))
