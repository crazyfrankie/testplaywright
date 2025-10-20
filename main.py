from playwright.sync_api import sync_playwright
import time

def automate_crazyfrank_blog():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=800)
        page = browser.new_page()
        
        print("开始自动化测试")
        
        # 访问网站
        print("访问网站...")
        page.goto("https://www.crazyfrank.top")
        page.wait_for_load_state("networkidle")
        
        # 获取网站标题
        title = page.title()
        print(f"网站标题: {title}")
        
        # 1. 测试主题切换
        print("测试主题切换...")
        theme_switch = page.locator(".theme-switch").first
        theme_switch.click()
        time.sleep(1)
        theme_switch.click()  # 切换回来
        
        # 2. 测试导航菜单
        print("测试导航菜单...")
        
        # 点击"文章"
        posts_link = page.locator("a[href='/zh/posts/']").first
        posts_link.click()
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        
        # 点击"标签"
        page.locator("a[href='/zh/tags/']").first.click()
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        
        # 点击"分类"
        page.locator("a[href='/zh/categories/']").first.click()
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        
        # 3. 返回首页
        print("返回首页...")
        page.locator("a[href='/zh/']").first.click()
        page.wait_for_load_state("networkidle")
        
        # 4. 获取文章列表信息
        print("获取文章信息...")
        articles = page.locator("article.single.summary")
        article_count = articles.count()
        print(f"首页文章数量: {article_count}")
        
        # 获取前3篇文章标题
        for i in range(min(3, article_count)):
            article_title = articles.nth(i).locator("h1 a").text_content()
            print(f"  {i+1}. {article_title}")
        
        # 5. 点击第一篇文章
        print("访问第一篇文章...")
        first_article = articles.first.locator("h1 a")
        first_article.click()
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        # 获取文章内容信息
        article_title = page.locator("h1").first.text_content()
        print(f"当前文章: {article_title}")
        
        # 滚动阅读
        page.evaluate("window.scrollTo(0, document.body.scrollHeight/3)")
        time.sleep(1)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
        time.sleep(1)
        
        # 6. 返回首页获取社交链接
        print("获取社交链接...")
        page.goto("https://www.crazyfrank.top/zh/")
        page.wait_for_load_state("networkidle")
        
        # 获取GitHub链接 (使用first避免多个匹配)
        github_link = page.locator("a[title='GitHub']").first
        if github_link.count() > 0:
            github_url = github_link.get_attribute("href")
            print(f"GitHub: {github_url}")
        
        # 获取邮箱链接
        email_link = page.locator("a[title='Email']")
        if email_link.count() > 0:
            email_url = email_link.get_attribute("href")
            print(f"Email: {email_url}")
        
        # 7. 截图保存
        print("保存截图...")
        page.screenshot(path="crazyfrank.png", full_page=True)
        
        # 8. 获取网站统计信息
        print("网站统计:")
        nav_links = page.locator(".menu-item")
        print(f"  导航链接数: {nav_links.count()}")
        
        social_links = page.locator(".links a")
        print(f"  社交链接数: {social_links.count()}")
        
        browser.close()
        print("自动化测试完成!")
        print("截图已保存为: crazyfrank.png")

if __name__ == "__main__":
    automate_crazyfrank_blog()
