#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音自动回复评论工具

功能：
1. 读取采集到的评论数据
2. 筛选符合条件的评论
3. 自动在抖音上回复评论

⚠️ 重要警告：
- 自动评论可能违反抖音服务条款
- 可能导致账号被限制或封禁
- 请谨慎使用，建议使用小号测试
- 严格控制回复频率和数量
"""

import asyncio
import csv
import random
import os
from typing import List, Dict
from playwright.async_api import async_playwright, Page, BrowserContext
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))
import config


class AutoReplyComments:
    """自动回复评论类"""

    def __init__(self):
        self.browser_context = None
        self.page = None

    async def init_browser(self):
        """初始化浏览器"""
        print("🔄 正在启动浏览器...")
        playwright = await async_playwright().start()
        chromium = playwright.chromium

        # 使用与登录相同的用户数据目录
        user_data_dir = os.path.join(os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM)

        if not os.path.exists(user_data_dir):
            print("❌ 未找到登录数据！请先运行 python run_douyin.py 并完成登录")
            return False

        self.browser_context = await chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,  # 显示浏览器便于观察
            viewport={"width": 1920, "height": 1080},
        )

        self.page = await self.browser_context.new_page()
        print("✅ 浏览器启动成功")
        return True

    def read_comments_from_csv(self, csv_file: str) -> List[Dict]:
        """从CSV文件读取评论数据"""
        comments = []

        if not os.path.exists(csv_file):
            print(f"❌ 文件不存在: {csv_file}")
            return comments

        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                comments.append(row)

        print(f"✅ 从 {csv_file} 读取了 {len(comments)} 条评论")
        return comments

    def filter_comments(self, comments: List[Dict], keywords: List[str] = None) -> List[Dict]:
        """筛选评论"""
        if not keywords:
            return comments

        filtered = []
        for comment in comments:
            content = comment.get('content', '') or comment.get('评论内容', '')
            # 检查是否包含任何关键词
            if any(keyword in content for keyword in keywords):
                filtered.append(comment)

        print(f"✅ 筛选后剩余 {len(filtered)} 条评论")
        return filtered

    async def reply_to_comment(self, video_url: str, comment_id: str, reply_text: str):
        """在指定视频下回复评论"""
        try:
            # 访问视频页面
            print(f"\n📍 访问视频: {video_url}")
            await self.page.goto(video_url, wait_until="networkidle")
            await asyncio.sleep(random.uniform(2, 4))

            # 等待评论区加载
            print("⏳ 等待评论区加载...")
            await asyncio.sleep(3)

            # 查找目标评论并点击回复按钮
            print(f"🔍 查找评论 ID: {comment_id}")

            # 注意：这里需要根据实际的DOM结构调整选择器
            # 以下是示例代码，可能需要根据实际情况修改

            # 方法1: 滚动到评论区
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await asyncio.sleep(2)

            # 方法2: 点击评论按钮（打开评论列表）
            try:
                comment_button = await self.page.wait_for_selector('[data-e2e="comment-button"]', timeout=5000)
                if comment_button:
                    await comment_button.click()
                    await asyncio.sleep(2)
            except:
                print("ℹ️  评论区可能已经打开")

            # 方法3: 找到回复输入框并输入内容
            print(f"✍️  输入回复内容: {reply_text}")

            # 尝试找到评论输入框
            input_selector = 'textarea[placeholder*="评论"], textarea[data-e2e="comment-input"]'
            input_box = await self.page.wait_for_selector(input_selector, timeout=10000)

            if input_box:
                # 点击输入框
                await input_box.click()
                await asyncio.sleep(1)

                # 输入回复内容（模拟人工输入，逐字输入）
                for char in reply_text:
                    await input_box.type(char, delay=random.randint(50, 150))

                await asyncio.sleep(1)

                # 查找发送按钮
                send_button = await self.page.wait_for_selector('[data-e2e="comment-post"], button:has-text("发布")', timeout=5000)

                if send_button:
                    print("📤 准备发送回复...")
                    # 等待用户确认（安全机制）
                    print("\n⚠️  请在浏览器中检查回复内容")
                    print("⚠️  如果内容正确，程序将在5秒后自动发送")
                    print("⚠️  如需取消，请按 Ctrl+C")

                    await asyncio.sleep(5)

                    # 点击发送
                    await send_button.click()
                    print("✅ 回复已发送！")
                    return True
                else:
                    print("❌ 未找到发送按钮")
                    return False
            else:
                print("❌ 未找到评论输入框")
                return False

        except Exception as e:
            print(f"❌ 回复失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def auto_reply_batch(self, comments: List[Dict], reply_templates: List[str], max_count: int = 10):
        """批量自动回复评论"""
        print(f"\n🚀 开始批量回复 (最多 {max_count} 条)")
        print(f"📝 回复模板: {reply_templates}")
        print("-" * 60)

        success_count = 0

        for i, comment in enumerate(comments[:max_count]):
            print(f"\n[{i+1}/{min(len(comments), max_count)}]")

            # 获取视频URL和评论ID
            video_url = comment.get('video_url') or comment.get('视频链接')
            comment_id = comment.get('comment_id') or comment.get('评论ID')
            content = comment.get('content') or comment.get('评论内容')

            if not video_url:
                print("⚠️  跳过：缺少视频URL")
                continue

            print(f"📖 原评论: {content[:50]}...")

            # 随机选择一个回复模板
            reply_text = random.choice(reply_templates)
            print(f"💬 将回复: {reply_text}")

            # 执行回复
            success = await self.reply_to_comment(video_url, comment_id, reply_text)

            if success:
                success_count += 1
                print("✅ 回复成功")
            else:
                print("❌ 回复失败")

            # 随机延迟（30-60秒）避免被检测
            if i < min(len(comments), max_count) - 1:
                delay = random.randint(30, 60)
                print(f"\n⏰ 等待 {delay} 秒后继续...")
                await asyncio.sleep(delay)

        print("\n" + "=" * 60)
        print(f"✅ 批量回复完成！成功: {success_count}/{min(len(comments), max_count)}")
        print("=" * 60)

    async def close(self):
        """关闭浏览器"""
        if self.browser_context:
            await self.browser_context.close()


async def main():
    """主函数"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║           抖音自动回复评论工具                            ║
║                                                           ║
║  ⚠️  警告：                                              ║
║  - 自动评论可能违反抖音服务条款                          ║
║  - 可能导致账号被限制或封禁                              ║
║  - 请谨慎使用，建议使用小号测试                          ║
║  - 严格控制回复频率（建议每条间隔30-60秒）              ║
╚═══════════════════════════════════════════════════════════╝
    """)

    # 确认使用
    confirm = input("\n⚠️  您确定要继续吗？ [yes/no] (默认:no): ").strip().lower()
    if confirm != 'yes':
        print("已取消")
        return

    # 初始化
    tool = AutoReplyComments()

    if not await tool.init_browser():
        return

    try:
        # 步骤1: 选择评论数据文件
        print("\n" + "=" * 60)
        print("步骤1: 选择评论数据文件")
        print("=" * 60)

        # 查找data目录下的CSV文件
        data_dir = "data/douyin/csv"
        if os.path.exists(data_dir):
            csv_files = [f for f in os.listdir(data_dir) if f.endswith('_comments.csv')]
            if csv_files:
                print("\n可用的评论文件：")
                for i, file in enumerate(csv_files):
                    print(f"  {i+1}. {file}")

                choice = input(f"\n请选择文件 [1-{len(csv_files)}]: ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(csv_files):
                    csv_file = os.path.join(data_dir, csv_files[int(choice)-1])
                else:
                    print("❌ 无效选择")
                    return
            else:
                print("❌ 未找到评论文件")
                return
        else:
            csv_file = input("\n请输入评论CSV文件路径: ").strip()

        # 步骤2: 读取评论
        comments = tool.read_comments_from_csv(csv_file)
        if not comments:
            return

        # 步骤3: 筛选评论（可选）
        print("\n" + "=" * 60)
        print("步骤2: 筛选评论（可选）")
        print("=" * 60)

        use_filter = input("\n是否筛选评论？[y/n] (默认:n): ").strip().lower()

        if use_filter == 'y':
            keywords_input = input("请输入关键词（多个用逗号分隔，如：好用,推荐）: ").strip()
            if keywords_input:
                keywords = [k.strip() for k in keywords_input.split(',')]
                comments = tool.filter_comments(comments, keywords)

        if not comments:
            print("❌ 没有符合条件的评论")
            return

        # 步骤4: 设置回复内容
        print("\n" + "=" * 60)
        print("步骤3: 设置回复内容")
        print("=" * 60)

        print("\n请输入回复模板（每行一个，输入空行结束）：")
        print("示例：")
        print("  正巧我也有")
        print("  我家也有哦")
        print("  同款！")
        print()

        reply_templates = []
        while True:
            template = input(f"模板{len(reply_templates)+1}: ").strip()
            if not template:
                break
            reply_templates.append(template)

        if not reply_templates:
            print("❌ 未设置回复模板")
            return

        # 步骤5: 设置回复数量
        print("\n" + "=" * 60)
        print("步骤4: 设置回复数量")
        print("=" * 60)

        max_count_input = input(f"\n最多回复多少条评论？ (默认:10, 建议不超过20): ").strip()
        max_count = int(max_count_input) if max_count_input.isdigit() else 10

        # 最终确认
        print("\n" + "=" * 60)
        print("确认信息")
        print("=" * 60)
        print(f"评论总数: {len(comments)}")
        print(f"将回复: {min(len(comments), max_count)} 条")
        print(f"回复模板: {reply_templates}")
        print(f"预计耗时: {min(len(comments), max_count) * 0.75} 分钟（每条约45秒）")
        print("-" * 60)

        final_confirm = input("\n确认开始批量回复？ [yes/no] (默认:no): ").strip().lower()
        if final_confirm != 'yes':
            print("已取消")
            return

        # 执行批量回复
        await tool.auto_reply_batch(comments, reply_templates, max_count)

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await tool.close()


if __name__ == "__main__":
    asyncio.run(main())
