#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
百度事件评论爬虫 - 主执行脚本
使用优化后的爬虫进行完整爬取
"""

import time
import os
import sys
from level1_scraper import Level1Scraper
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """主函数 - 使用优化后的爬虫"""
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