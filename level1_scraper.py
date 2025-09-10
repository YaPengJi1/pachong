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
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
import os
from level2_scraper import Level2Scraper

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
            
            # 尝试初始化WebDriver
            logger.info("正在初始化Chrome WebDriver...")
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            logger.info("Selenium WebDriver 初始化成功")
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
            
            # 优化的滚动策略以加载所有164个事件
            logger.info("正在滚动页面以加载更多内容...")
            
            # 先点击一次时间排序按钮（只点击一次）
            try:
                time_order_btn = self.driver.find_element(By.CSS_SELECTOR, ".btn-order")
                if time_order_btn.is_displayed():
                    logger.info("点击时间排序按钮...")
                    self.driver.execute_script("arguments[0].click();", time_order_btn)
                    time.sleep(3)
            except:
                pass
            
            # 滚动加载内容
            for i in range(15):  # 减少滚动次数
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # 增加等待时间确保内容加载
                
                # 检查是否有"加载更多"按钮（排除时间排序按钮）
                try:
                    load_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button, .load-more, .more-btn, [class*='load'], [class*='more']")
                    for btn in load_buttons:
                        if btn.is_displayed() and ('加载' in btn.text or '更多' in btn.text or 'load' in btn.text.lower() or 'more' in btn.text.lower()):
                            logger.info(f"发现加载按钮: {btn.text}")
                            self.driver.execute_script("arguments[0].click();", btn)
                            time.sleep(3)
                            break
                except:
                    pass
            
            # 最后等待一下确保所有内容加载完成
            time.sleep(5)
            
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
                '.event-item'
            ]
            
            for selector in selectors:
                items = soup.select(selector)
                if len(items) > len(event_items):
                    event_items = items
                    logger.info(f"使用选择器 '{selector}' 找到 {len(items)} 个事件项")
            
            logger.info(f"最终找到 {len(event_items)} 个事件项")
            
            for i, item in enumerate(event_items):
                try:
                    sub_event = self._extract_event_from_item(item, i+1)
                    if sub_event:
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
    
    def start_level2_scraping(self):
        """启动二级评论爬取"""
        logger.info("开始启动二级评论爬取...")
        
        try:
            # 创建二级爬虫实例
            level2_scraper = Level2Scraper(self.core_info.get('core_event_name', ''))
            
            # 开始爬取评论
            total_comments = level2_scraper.scrape_all_comments(self.sub_events)
            
            # 显示摘要
            level2_scraper.print_summary()
            
            # 关闭资源
            level2_scraper.close()
            
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
                
                # 询问是否继续爬取评论
                print(f"\n🤔 是否开始爬取评论？(y/n): ", end="")
                user_input = input().strip().lower()
                
                if user_input in ['y', 'yes', '是', '']:
                    print(f"\n🚀 开始爬取评论...")
                    total_comments = scraper.start_level2_scraping()
                    print(f"\n🎉 完整爬取完成！")
                    print(f"📊 总评论数: {total_comments}")
                    print(f"📄 JSON文件: data/level2_data.json")
                    print(f"📊 Excel文件: data/{scraper._sanitize_filename(scraper.core_info['core_event_name'])}_评论数据.xlsx")
                else:
                    print(f"\n⏸️ 跳过评论爬取")
            else:
                print("❌ 子事件爬取失败")
        else:
            print("❌ 核心信息爬取失败")
        
    finally:
        scraper.close()

if __name__ == "__main__":
    main()
