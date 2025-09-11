#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
百度事件评论爬虫 - 一级界面爬虫
从主时间线页面提取核心信息和子事件列表
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
import os
from level2_scraper import Level2Scraper
from data_manager import DataManager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Level1Scraper:
    def __init__(self):
        self.session = requests.Session()
        self.driver = None
        self.core_info = {}
        self.sub_events = []
        self._init_session()
        self._init_selenium()
        self._ensure_data_dir()
    
    def _init_session(self):
        """初始化requests会话"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.baidu.com/',
        })
    
    def _init_selenium(self):
        """初始化Selenium"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-logging')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # 优先尝试：Selenium Manager（不下载第三方依赖）
            try:
                logger.info("正在初始化Chrome（Selenium Manager）...")
                self.driver = webdriver.Chrome(options=chrome_options)
                self.driver.set_page_load_timeout(30)
                logger.info("Selenium WebDriver 初始化成功 (Chrome)")
                return
            except Exception as e1:
                logger.warning(f"Chrome (Selenium Manager) 初始化失败: {e1}")

            # 备用方案：本地驱动（不进行网络下载）
            try:
                logger.info("尝试使用本地chromedriver（跳过网络下载）...")
                os.environ['WDM_LOCAL'] = '1'  # 禁止webdriver-manager联网下载，若无本地缓存将快速失败
                chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '')
                if chromedriver_path and os.path.exists(chromedriver_path):
                    logger.info(f"使用环境变量CHROMEDRIVER_PATH: {chromedriver_path}")
                    self.driver = webdriver.Chrome(service=ChromeService(chromedriver_path), options=chrome_options)
                    self.driver.set_page_load_timeout(30)
                    logger.info("Selenium WebDriver 初始化成功 (本地chromedriver)")
                    return
            except Exception as e2:
                logger.warning(f"本地chromedriver 初始化失败: {e2}")

            # 最后备用：Microsoft Edge（Windows更易可用）
            try:
                logger.info("尝试使用Edge WebDriver 初始化...")
                edge_options = EdgeOptions()
                edge_options.use_chromium = True
                edge_options.add_argument('--headless')
                edge_options.add_argument('--no-sandbox')
                edge_options.add_argument('--disable-dev-shm-usage')
                edge_options.add_argument('--disable-gpu')
                edge_options.add_argument('--disable-extensions')
                edge_options.add_argument('--disable-logging')
                edge_options.add_argument('--disable-web-security')
                edge_options.add_argument('--window-size=1920,1080')
                self.driver = webdriver.Edge(options=edge_options)
                self.driver.set_page_load_timeout(30)
                logger.info("Selenium WebDriver 初始化成功 (Edge)")
                return
            except Exception as e3:
                logger.error(f"Edge 初始化失败: {e3}")

            # 全部失败
            raise RuntimeError("无法初始化任何浏览器驱动。请安装 Chrome/Edge 或提供 CHROMEDRIVER_PATH。")
        except Exception as e:
            logger.error(f"Selenium WebDriver 初始化失败: {e}")
            logger.error("请确保已安装Chrome浏览器和ChromeDriver")
            self.driver = None
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        if not os.path.exists('data'):
            os.makedirs('data')
            logger.info("创建数据目录: data")
    
    def _sanitize_filename(self, filename):
        """清理文件名，移除非法字符"""
        if not filename:
            return "未知事件"
        # 移除或替换非法字符
        illegal_chars = r'[<>:"/\\|?*]'
        filename = re.sub(illegal_chars, '_', filename)
        # 限制长度
        if len(filename) > 50:
            filename = filename[:50]
        return filename
    
    def scrape_core_info(self, url):
        """爬取核心信息"""
        logger.info(f"开始爬取核心信息: {url}")
        
        if not self.driver:
            logger.error("WebDriver未初始化，无法爬取")
            return False
        
        try:
            logger.info("正在访问页面...")
            self.driver.get(url)
            
            logger.info("等待页面加载...")
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            logger.info("页面加载完成，开始解析...")
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # 1. 核心事件名称
            title_elem = soup.find('title')
            core_event_name = title_elem.get_text(strip=True) if title_elem else ''
            
            # 2. 最新更新时间
            update_time_elem = soup.find('p', class_='create-time')
            update_time = update_time_elem.get_text(strip=True) if update_time_elem else ''
            
            # 3. 子事件数量 - 从标签中获取
            sub_event_count = 0
            count_elem = soup.find('span', class_='count')
            if count_elem:
                try:
                    sub_event_count = int(count_elem.get_text(strip=True))
                except ValueError:
                    pass
            
            self.core_info = {
                'core_event_name': core_event_name,
                'update_time': update_time,
                'sub_event_count': sub_event_count,
                'scrape_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(f"核心信息提取完成:")
            logger.info(f"  事件名称: {core_event_name}")
            logger.info(f"  更新时间: {update_time}")
            logger.info(f"  子事件数量: {sub_event_count}")
            
            return True
            
        except Exception as e:
            logger.error(f"爬取核心信息失败: {e}")
            return False
    
    def scrape_sub_events(self, url):
        """爬取164个子事件"""
        logger.info("开始爬取子事件列表...")
        
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 等待初始内容加载
            time.sleep(3)
            
            # 动态加载：循环滚动 + 点击“加载更多”，直到元素数量稳定
            logger.info("正在滚动页面以加载更多内容...")
            stable_loops = 0
            last_count = -1
            max_loops = 80

            def query_item_count():
                try:
                    return int(self.driver.execute_script(
                        "return document.querySelectorAll(`div.item, div[class*=item], div[class*=event], li[class*=item], li[class*=event], .timeline-item, .event-item`).length;")
                    )
                except Exception:
                    return 0

            # 若页面提供总数，作为退出参考
            declared_total = 0
            try:
                declared_total = int(self.core_info.get('sub_event_count', 0))
            except Exception:
                declared_total = 0

            for i in range(max_loops):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)

                # 尝试点击“加载更多/展开”
                try:
                    load_buttons = self.driver.find_elements(By.XPATH, "//button[contains(., '加载') or contains(., '更多') or contains(translate(., 'MORE', 'more'), 'more') or contains(translate(., 'LOAD', 'load'), 'load')] | //*[(contains(@class, 'load') or contains(@class, 'more')) and self::button] | //a[contains(., '加载') or contains(., '更多')]")
                    clicked = False
                    for btn in load_buttons:
                        if btn.is_displayed() and btn.is_enabled():
                            try:
                                self.driver.execute_script("arguments[0].click();", btn)
                                clicked = True
                                time.sleep(2)
                            except Exception:
                                continue
                    if clicked:
                        time.sleep(1)
                except Exception:
                    pass

                count_now = query_item_count()
                logger.debug(f"加载循环 {i+1}: 当前事件项 {count_now}")

                if count_now == last_count:
                    stable_loops += 1
                else:
                    stable_loops = 0
                last_count = count_now

                # 退出条件：稳定多次或达到声明总数
                if (declared_total and count_now >= declared_total) or stable_loops >= 5:
                    break

            # 最后等待一下确保所有内容加载完成
            time.sleep(2)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # 尝试多种可能的选择器
            event_items = []
            selectors = [
                'div.item',
                'div[class*="item"]',
                'div[class*="event"]',
                'li[class*="item"]',
                'li[class*="event"]',
                '.timeline-item',
                '.event-item',
                'section[class*="item"]',
            ]
            for selector in selectors:
                items = soup.select(selector)
                if items and len(items) > len(event_items):
                    event_items = items
                    logger.info(f"使用选择器 '{selector}' 找到 {len(items)} 个事件项")
            
            logger.info(f"最终找到 {len(event_items)} 个事件项")
            
            seen_keys = set()
            for i, item in enumerate(event_items):
                try:
                    sub_event = self._extract_event_from_item(item, i+1)
                    if sub_event:
                        key = (sub_event.get('title', ''), sub_event.get('time', ''))
                        if key not in seen_keys:
                            seen_keys.add(key)
                            self.sub_events.append(sub_event)
                except Exception as e:
                    logger.warning(f"解析事件项 {i+1} 失败: {e}")
                    continue
            
            logger.info(f"成功提取 {len(self.sub_events)} 个子事件")
            
            # 显示前几个子事件预览
            for i, event in enumerate(self.sub_events[:5]):
                logger.info(f"子事件 {i+1}: {event['title'][:50]}... - {event['time']}")
            
            return True
            
        except Exception as e:
            logger.error(f"爬取子事件失败: {e}")
            return False
    
    def _extract_event_from_item(self, item, index):
        """从单个item元素中提取事件信息"""
        sub_event = {
            'id': f'event_{index}',
            'title': '',
            'link': '',
            'time': '',
            'summary': '',
            'author': ''
        }
        
        # 提取时间
        time_elem = item.find('span', class_='time')
        if time_elem:
            sub_event['time'] = time_elem.get_text(strip=True)
        
        # 提取标题和链接
        title_link = item.find('a', class_='content-link')
        if title_link:
            sub_event['title'] = title_link.get_text(strip=True)
            sub_event['link'] = title_link.get('href', '')
        
        # 提取摘要和作者
        dynamic_container = item.find('a', class_='dynamic-container')
        if dynamic_container:
            # 提取作者
            author_elem = dynamic_container.find('div', class_='dynamic-author')
            if author_elem:
                author_text = author_elem.get_text(strip=True)
                sub_event['author'] = author_text.replace('：', '').replace(':', '')
            
            # 提取摘要
            content_elem = dynamic_container.find('div', class_='dynamic-content')
            if content_elem:
                sub_event['summary'] = content_elem.get_text(strip=True)
        
        # 只有当标题不为空时才返回
        if sub_event['title']:
            return sub_event
        
        return None
    
    def save_data(self, filename='data/level1_data.json'):
        """保存数据"""
        try:
            output_data = {
                'core_info': self.core_info,
                'sub_events': self.sub_events,
                'total_sub_events': len(self.sub_events),
                'scrape_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"数据已保存到 {filename}")
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
    
    def start_level2_scraping(self, output_dir: str = None, csv_output_file: str = None):
        """启动二级评论爬取"""
        logger.info("开始启动二级评论爬取...")
        
        try:
            # 创建二级爬虫实例
            level2_scraper = Level2Scraper(
                self.core_info.get('core_event_name', ''),
                output_dir=output_dir,
                csv_output_file=csv_output_file
            )
            
            # 开始爬取评论
            total_comments = level2_scraper.scrape_all_comments(self.sub_events)
            
            # 显示摘要
            level2_scraper.print_summary()
            
            # 关闭资源
            level2_scraper.close()
            
            # 生成合并数据到同一目录
            try:
                dm = DataManager(output_dir or 'data')
                dm.combine_data()
            except Exception as _:
                logger.warning("合并数据失败，但不影响主流程")

            logger.info(f"二级评论爬取完成，共获取 {total_comments} 条评论")
            return total_comments
            
        except Exception as e:
            logger.error(f"二级评论爬取失败: {e}")
            return 0
    
    def print_summary(self):
        """打印摘要信息"""
        print("\n" + "="*60)
        print("一级界面爬取结果摘要")
        print("="*60)
        print(f"核心事件: {self.core_info.get('core_event_name', '未获取')}")
        print(f"更新时间: {self.core_info.get('update_time', '未获取')}")
        print(f"子事件数量: {self.core_info.get('sub_event_count', 0)}")
        print(f"实际提取: {len(self.sub_events)} 个子事件")
        
        if self.sub_events:
            print(f"\n前5个子事件:")
            for i, event in enumerate(self.sub_events[:5]):
                print(f"{i+1}. {event['time']} - {event['title'][:50]}...")
                if event['author']:
                    print(f"   作者: {event['author']}")
                if event['summary']:
                    print(f"   摘要: {event['summary'][:80]}...")
                print()
        
        print("="*60)
    
    def close(self):
        """关闭资源"""
        if self.driver:
            self.driver.quit()
        self.session.close()

def main():
    """主函数"""
    # 可替换为其他核心事件页面URL
    target_url = "https://events.baidu.com/search/vein?platform=pc&record_id=648521&query=%E4%B8%AD%E5%9B%BD%E4%BA%BA%E6%B0%91%E6%8A%97%E6%97%A5%E6%88%98%E4%BA%89%E6%9A%A8%E4%B8%96%E7%95%8C%E5%8F%8D%E6%B3%95%E8%A5%BF%E6%96%AF%E6%88%98%E4%BA%89%E8%83%9C%E5%88%A980%E5%91%A8%E5%B9%B4%E7%BA%AA%E5%BF%B5%E6%97%A5&srcid=50367"
    
    scraper = Level1Scraper()
    try:
        # 爬取核心信息
        if scraper.scrape_core_info(target_url):
            # 爬取子事件
            if scraper.scrape_sub_events(target_url):
                scraper.save_data()
                print(f"\n✅ 一级界面爬取完成!")
                print(f"📊 核心事件: {scraper.core_info['core_event_name']}")
                print(f"📊 更新时间: {scraper.core_info['update_time']}")
                print(f"📊 子事件数量: {scraper.core_info['sub_event_count']}")
                print(f"📊 实际提取: {len(scraper.sub_events)} 个子事件")
                print(f"📄 数据保存: data/level1_data.json")
                
                # 显示摘要
                scraper.print_summary()
                
                # 自动启动二级爬取（去除交互）
                print(f"\n🚀 开始爬取评论...")
                total_comments = scraper.start_level2_scraping()
                print(f"\n🎉 完整爬取完成！")
                print(f"📊 总评论数: {total_comments}")
                print(f"📄 JSON文件: data/level2_data.json")
                print(f"📊 Excel文件: data/{scraper._sanitize_filename(scraper.core_info['core_event_name'])}_评论数据.xlsx")
            else:
                print("❌ 子事件爬取失败")
        else:
            print("❌ 核心信息爬取失败")
        
    finally:
        scraper.close()

if __name__ == "__main__":
    main()
