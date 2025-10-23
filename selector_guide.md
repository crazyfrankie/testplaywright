# Playwright 选择器完整手册

## 基础选择器

### 1. 标签选择器
```python
page.locator("div")        # 所有div标签
page.locator("a")          # 所有a标签
page.locator("input")      # 所有input标签
page.locator("button")     # 所有button标签
```

### 2. Class选择器 (用 .)
```python
page.locator(".menu")           # class="menu"
page.locator(".btn.primary")    # 同时有btn和primary两个class
page.locator("div.container")   # div标签且有container class
```

### 3. ID选择器 (用 #)
```python
page.locator("#header")         # id="header"
page.locator("#login-form")     # id="login-form"
page.locator("div#main")        # div标签且id="main"
```

### 4. 属性选择器 (用 [])
```python
page.locator("[href]")                    # 有href属性
page.locator("[type='text']")             # type属性等于text
page.locator("[class*='btn']")            # class包含btn
page.locator("[href^='https']")           # href以https开头
page.locator("[href$='.pdf']")            # href以.pdf结尾
page.locator("[data-id='123']")           # data-id等于123
```

## 关系选择器

### 1. 后代选择器 (空格)
```python
page.locator("div a")           # div下的所有a标签(任意层级)
page.locator(".menu li")        # menu class下的所有li
page.locator("form input")      # form下的所有input
```

### 2. 直接子元素 (>)
```python
page.locator("ul > li")         # ul的直接子li元素
page.locator(".nav > a")        # nav class的直接子a元素
```

### 3. 相邻兄弟 (+)
```python
page.locator("h1 + p")          # h1后面紧邻的p元素
page.locator(".title + .content") # title后面紧邻的content
```

### 4. 通用兄弟 (~)
```python
page.locator("h1 ~ p")          # h1后面的所有p兄弟元素
```

## 伪类选择器

### 1. 位置伪类
```python
page.locator("li:first-child")     # 第一个li子元素
page.locator("li:last-child")      # 最后一个li子元素
page.locator("li:nth-child(2)")    # 第二个li子元素
page.locator("li:nth-child(odd)")  # 奇数位置的li
page.locator("li:nth-child(even)") # 偶数位置的li
```

### 2. 状态伪类
```python
page.locator("input:checked")      # 选中的input
page.locator("input:disabled")     # 禁用的input
page.locator("input:enabled")      # 启用的input
page.locator("a:hover")            # 鼠标悬停的a标签
```

### 3. 内容伪类
```python
page.locator("div:empty")          # 空的div元素
page.locator("p:not(.hidden)")     # 没有hidden class的p元素
```

## Playwright 特有选择器

### 1. 文本选择器
```python
page.locator("text=登录")                    # 包含"登录"文本
page.locator("text='精确匹配'")              # 精确匹配文本
page.locator("text=/正则.*表达式/")          # 正则表达式匹配
page.locator("button:has-text('提交')")     # button包含"提交"文本
```

### 2. 可见性选择器
```python
page.locator("button:visible")             # 可见的button
page.locator("div:hidden")                 # 隐藏的div
```

### 3. 角色选择器
```python
page.locator("role=button")                # 按钮角色
page.locator("role=textbox")               # 文本框角色
page.locator("role=link")                  # 链接角色
page.locator("role=heading")               # 标题角色
```

### 4. 测试ID选择器
```python
page.locator("[data-testid='submit-btn']") # 测试ID
page.get_by_test_id("submit-btn")          # 简化写法
```

## 组合选择器

### 1. 多条件组合
```python
page.locator("input[type='text'].required")     # input且type=text且有required class
page.locator("div.card:has(h2)")                # 包含h2的card div
page.locator("button:not(.disabled):visible")   # 可见且非disabled的button
```

### 2. 复杂嵌套
```python
page.locator(".sidebar .menu li:first-child a")           # 复杂嵌套
page.locator("form:has(.error) input[type='email']")      # 有错误的表单中的邮箱输入框
page.locator("table tbody tr:nth-child(2) td:last-child") # 表格第二行最后一列
```

## 实用方法

### 1. 定位方法
```python
# 基础定位
page.locator("selector")

# 按文本定位
page.get_by_text("文本")
page.get_by_label("标签")
page.get_by_placeholder("占位符")

# 按角色定位
page.get_by_role("button", name="提交")

# 按测试ID定位
page.get_by_test_id("test-id")
```

### 2. 筛选方法
```python
locator = page.locator("li")
locator.first                    # 第一个
locator.last                     # 最后一个
locator.nth(2)                   # 第三个(索引从0开始)
locator.filter(has_text="文本")   # 包含特定文本的
locator.filter(has=page.locator("span"))  # 包含span的
```

### 3. 操作方法
```python
locator.click()                  # 点击
locator.fill("文本")             # 填入文本
locator.type("文本")             # 逐字输入
locator.check()                  # 选中复选框
locator.select_option("值")      # 选择下拉选项
```

### 4. 获取信息
```python
locator.text_content()           # 获取文本内容
locator.inner_text()             # 获取内部文本
locator.inner_html()             # 获取内部HTML
locator.get_attribute("href")    # 获取属性值
locator.is_visible()             # 是否可见
locator.is_enabled()             # 是否启用
locator.count()                  # 元素数量
```

## 常见场景示例

### 1. 表单操作
```python
# 登录表单
page.locator("input[name='username']").fill("用户名")
page.locator("input[type='password']").fill("密码")
page.locator("button[type='submit']").click()

# 下拉选择
page.locator("select#country").select_option("中国")
```

### 2. 表格操作
```python
# 表格第二行第三列
page.locator("table tr:nth-child(2) td:nth-child(3)")

# 包含特定文本的行
page.locator("tr:has-text('张三')")
```

### 3. 导航菜单
```python
# 主菜单项
page.locator("nav .menu-item")

# 子菜单
page.locator(".dropdown-menu a")
```

### 4. 动态内容
```python
# 等待元素出现
page.wait_for_selector(".loading", state="hidden")
page.locator(".content").wait_for()

# 等待文本出现
page.wait_for_selector("text=加载完成")
```

## 调试技巧

### 1. 元素高亮
```python
locator.highlight()              # 高亮显示元素
```

### 2. 截图调试
```python
page.screenshot(path="debug.png")
locator.screenshot(path="element.png")
```

### 3. 控制台输出
```python
print(f"找到 {locator.count()} 个元素")
print(f"元素文本: {locator.text_content()}")
```

## 性能优化

### 1. 精确选择器
```python
# 好的做法
page.locator("[data-testid='submit']")
page.locator("#unique-id")

# 避免过于宽泛
page.locator("div")  # 太宽泛
```

### 2. 等待策略
```python
# 等待元素可见
locator.wait_for(state="visible")

# 等待元素隐藏
locator.wait_for(state="hidden")
```

### 3. 批量操作
```python
# 获取所有元素的文本
texts = page.locator(".item").all_text_contents()
```

