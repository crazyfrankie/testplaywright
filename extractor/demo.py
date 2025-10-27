"""
内容提取器演示脚本

独立运行的 Demo，用于测试内容提取功能
"""

import sys
import os
import csv
import json
import time
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from auto.extractor import JinaExtractor, BrowserExtractor, ExtractedContent


def load_urls_from_file(file_path: str) -> list[str]:
    """
    从文件加载 URL 列表
    
    支持格式：
    - .txt: 每行一个 URL
    - .csv: 支持多列，自动识别 URL 列
    
    Args:
        file_path: 文件路径
        
    Returns:
        list[str]: URL 列表
    """
    urls = []
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"❌ 文件不存在: {file_path}")
        return urls
    
    try:
        urls = load_urls_from_csv(file_path)
        
        print(f"✅ 从 {file_path.name} 加载了 {len(urls)} 个 URL")
        return urls
    
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return []

def load_urls_from_csv(file_path: Path) -> list[str]:
    """
    从 CSV 文件加载 URL
    
    支持的格式：
    1. 单列 CSV（只有 URL）
    2. 多列 CSV（自动识别包含 'url' 或 'link' 的列）
    3. 带表头的 CSV
    4. 无表头的 CSV（取第一列）
    """
    urls = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        # 尝试检测 CSV 格式
        sample = f.read(1024)
        f.seek(0)
        
        # 检测分隔符
        sniffer = csv.Sniffer()
        try:
            dialect = sniffer.sniff(sample)
            has_header = sniffer.has_header(sample)
        except:
            dialect = 'excel'
            has_header = False
        
        reader = csv.reader(f, dialect)
        rows = list(reader)
        
        if not rows:
            return urls
        
        # 如果有表头，查找 URL 列
        if has_header:
            headers = [h.lower().strip() for h in rows[0]]
            url_col_index = None
            
            # 查找包含 'url' 或 'link' 的列
            for i, header in enumerate(headers):
                if 'url' in header or 'link' in header:
                    url_col_index = i
                    break
            
            # 如果没找到，使用第一列
            if url_col_index is None:
                url_col_index = 0
            
            # 提取 URL
            for row in rows[1:]:
                if len(row) > url_col_index:
                    url = row[url_col_index].strip()
                    if url and url.startswith('http'):
                        urls.append(url)
        else:
            # 无表头，取第一列
            for row in rows:
                if row:
                    url = row[0].strip()
                    if url and url.startswith('http'):
                        urls.append(url)
    
    return urls

def save_results_to_json(results: list, output_file: str):
    """
    保存结果到 JSON 文件

    Args:
        results: 提取结果列表
        output_file: 输出文件路径
    """
    try:
        # 转换为字典列表
        data = [result.to_dict() for result in results]

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n✓ 结果已保存到: {output_file}")
    except Exception as e:
        print(f"\n❌ 保存结果失败: {e}")

def save_results_to_markdown(results: list, output_file: str):
    """
    保存结果到 Markdown 文件
    
    Args:
        results: 提取结果列表
        output_file: 输出文件路径
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# 内容提取结果\n\n")
            f.write(f"总计: {len(results)} 个链接\n\n")
            f.write("---\n\n")
            
            for i, result in enumerate(results, 1):
                f.write(f"## {i}. {result.title}\n\n")
                f.write(f"- **URL**: {result.url}\n")
                f.write(f"- **平台**: {result.platform}\n")
                f.write(f"- **字数**: {result.word_count}\n")
                f.write(f"- **状态**: {'✓ 成功' if result.success else f'✗ 失败: {result.error}'}\n")
                
                if result.author:
                    f.write(f"- **作者**: {result.author}\n")
                if result.publish_date:
                    f.write(f"- **发布日期**: {result.publish_date}\n")
                
                f.write(f"- **提取时间**: {result.extract_time}\n\n")
                
                if result.success and result.content:
                    f.write("### 内容预览\n\n")
                    # 只显示前 500 字符
                    preview = result.content[:500]
                    if len(result.content) > 500:
                        preview += "\n\n...(内容过长，已省略)..."
                    f.write(f"{preview}\n\n")
                
                f.write("---\n\n")
        
        print(f"✓ 结果已保存到: {output_file}")
    except Exception as e:
        print(f"❌ 保存结果失败: {e}")

def print_summary(results: list):
    """
    打印统计摘要
    
    Args:
        results: 提取结果列表
    """
    total = len(results)
    success = sum(1 for r in results if r.success)
    failed = total - success
    
    total_words = sum(r.word_count for r in results if r.success)
    avg_words = total_words // success if success > 0 else 0
    
    print("\n" + "="*60)
    print("📊 提取统计")
    print("="*60)
    print(f"总计: {total} 个链接")
    print(f"成功: {success} 个 ({success/total*100:.1f}%)")
    print(f"失败: {failed} 个 ({failed/total*100:.1f}%)")
    print(f"总字数: {total_words:,} 字")
    print(f"平均字数: {avg_words:,} 字/篇")
    print("="*60)

def print_result(result: ExtractedContent):
    """
    打印提取结果
    
    Args:
        result: 提取结果对象
    """
    print("\n" + "-"*60)
    print("📄 提取结果")
    print("-"*60)
    print(f"标题: {result.title}")
    print(f"平台: {result.platform}")
    print(f"Logo: {result.platform_logo}")
    print(f"字数: {result.word_count}")
    print(f"状态: {'✓ 成功' if result.success else f'✗ 失败: {result.error}'}")
    
    if result.author:
        print(f"作者: {result.author}")
    if result.publish_date:
        print(f"发布日期: {result.publish_date}")
    
    print(f"提取时间: {result.extract_time}")
    
    if result.processing_time is not None:
        print(f"处理耗时: {result.processing_time:.2f} 秒")
    
    if result.success and result.content:
        print("\n内容预览:")
        print("-"*60)
        preview = result.content[:300]
        if len(result.content) > 300:
            preview += "\n...(内容过长，已省略)..."
        print(preview)
    
    print("-"*60)

def test_single_url():
    """测试单个 URL"""
    print("\n" + "="*60)
    print("🔍 单个 URL 测试")
    print("="*60)
    
    url = input("\n请输入要测试的 URL: ").strip()
    
    if not url:
        print("❌ URL 不能为空")
        return
    
    print("\n选择提取器:")
    print("1. Jina 提取器（推荐）")
    print("2. 浏览器提取器")
    
    choice = input("\n请选择 (1-2): ").strip()
    
    if choice == "1":
        print("\n⏳ 使用 Jina 提取器...")
        extractor = JinaExtractor(timeout=30, api_key="jina_beda6e0b116a48aab8c13f6f0ed2a0c0synZFaRRgP1mXAgbxDdGsbxTZ1qm")
        result = extractor.extract(url)
        print_result(result)
    
    elif choice == "2":
        print("\n⏳ 使用浏览器提取器...")
        with BrowserExtractor(headless=False) as extractor:
            result = extractor.extract(url)
            print_result(result)
    
    else:
        print("❌ 无效选择")

def save_single_result(result: ExtractedContent, index: int, output_dir: Path):
    """
    保存单个提取结果到文件
    
    Args:
        result: 提取结果对象
        index: 序号
        output_dir: 输出目录
    """
    try:
        # 创建输出目录
        output_dir.mkdir(exist_ok=True)
        
        # 生成文件名（使用序号和标题的前20个字符）
        safe_title = "".join(c for c in result.title[:20] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')
        
        if not safe_title:
            safe_title = f"article_{index}"
        
        filename_base = f"{index:03d}_{safe_title}"
        
        # 保存 JSON 格式
        json_file = output_dir / f"{filename_base}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
            f.flush()  # 立即刷新缓冲区
            os.fsync(f.fileno())  # 强制写入磁盘
        
        # 保存 Markdown 格式
        md_file = output_dir / f"{filename_base}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# {result.title}\n\n")
            f.write(f"- **URL**: {result.url}\n")
            f.write(f"- **平台**: {result.platform}\n")
            f.write(f"- **字数**: {result.word_count}\n")
            f.write(f"- **状态**: {'✓ 成功' if result.success else f'✗ 失败: {result.error}'}\n")
            
            if result.author:
                f.write(f"- **作者**: {result.author}\n")
            if result.publish_date:
                f.write(f"- **发布日期**: {result.publish_date}\n")
            
            f.write(f"- **提取时间**: {result.extract_time}\n")
            
            if result.processing_time is not None:
                f.write(f"- **处理耗时**: {result.processing_time:.2f} 秒\n")
            
            f.write("\n")
            
            if result.success and result.content:
                f.write("## 正文内容\n\n")
                f.write(result.content)
            
            f.flush()  # 立即刷新缓冲区
            os.fsync(f.fileno())  # 强制写入磁盘
        
        print(f"  ✓ 已保存: {json_file.name} 和 {md_file.name}")
        
    except Exception as e:
        print(f"  ❌ 保存失败: {e}")

def test_batch_urls():
    """批量测试 URL"""
    print("\n" + "="*60)
    print("📦 批量 URL 测试")
    print("="*60)
    
    # 获取文件路径
    print("\n支持的文件格式:")
    print("  - test_urls.txt (默认)")
    print("  - url.csv")
    print("  - 或输入自定义文件路径")
    
    file_path = input("\n请输入文件路径 (直接回车使用 test_urls.txt): ").strip()
    
    if not file_path:
        file_path = "test_urls.txt"
    
    # 转换为绝对路径
    if not os.path.isabs(file_path):
        file_path = os.path.join(os.path.dirname(__file__), file_path)
    
    # 加载 URL
    urls = load_urls_from_file(file_path)
    
    if not urls:
        print("❌ 没有找到有效的 URL")
        return
    
    # 选择提取器
    print("\n选择提取器:")
    print("1. Jina 提取器（推荐）")
    print("2. 浏览器提取器")
    
    choice = input("\n请选择 (1-2): ").strip()
    
    # 创建输出目录
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    
    # 用于统计
    results = []
    
    if choice == "1":
        # 获取 API Key
        api_key = input("\n请输入 Jina API Key (直接回车跳过): ").strip() or None
        
        print(f"\n⏳ 使用 Jina 提取器处理 {len(urls)} 个 URL...")
        print(f"📁 结果将保存到: {output_dir}\n")
        extractor = JinaExtractor(timeout=30, api_key=api_key)
        
        for i, url in enumerate(urls, 1):
            print(f"\n{'='*60}")
            print(f"📍 [{i}/{len(urls)}] {url}")
            print('='*60)
            
            # 开始计时
            start_time = time.time()
            
            result = extractor.extract(url)
            
            # 计算耗时
            end_time = time.time()
            processing_time = end_time - start_time
            result.processing_time = processing_time
            
            print_result(result)
            
            # 立即保存结果
            save_single_result(result, i, output_dir)
            results.append(result)
            
            # 避免请求过快
            if i < len(urls):
                time.sleep(2)
    
    elif choice == "2":
        print(f"\n⏳ 使用浏览器提取器处理 {len(urls)} 个 URL...")
        print(f"📁 结果将保存到: {output_dir}\n")
        
        with BrowserExtractor(headless=False) as extractor:
            for i, url in enumerate(urls, 1):
                print(f"\n{'='*60}")
                print(f"📍 [{i}/{len(urls)}] {url}")
                print('='*60)
                
                # 开始计时
                start_time = time.time()
                
                result = extractor.extract(url)
                
                # 计算耗时
                end_time = time.time()
                processing_time = end_time - start_time
                result.processing_time = processing_time
                
                print_result(result)
                
                # 立即保存结果
                save_single_result(result, i, output_dir)
                results.append(result)
    
    else:
        print("❌ 无效选择")
        return
    
    # 打印统计摘要
    if results:
        print_summary(results)
        print(f"\n✅ 所有结果已保存到: {output_dir}")
        print(f"   - JSON 文件: {len(results)} 个")
        print(f"   - Markdown 文件: {len(results)} 个")

def main():
    """主函数"""
    print("="*60)
    print("🚀 内容提取器演示程序")
    print("="*60)
    
    while True:
        print("\n请选择测试模式:")
        print("1. 单个 URL 测试")
        print("2. 批量 URL 测试（支持 TXT/CSV）")
        print("0. 退出")
        
        choice = input("\n请选择 (0-5): ").strip()
        
        if choice == "0":
            print("\n结束")
            break

        elif choice == "1":
            test_single_url()
        
        elif choice == "2":
            test_batch_urls()
        
        else:
            print("❌ 无效选择，请重新输入")
        
        # 询问是否继续
        continue_test = input("\n是否继续测试？(y/n): ").strip().lower()
        if continue_test != 'y':
            print("\n👋 再见！")
            break


if __name__ == "__main__":
    main()