#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试完整工作流程
验证一级爬取和二级评论爬取的完整流程
"""

import os
import json
import pandas as pd
from level1_scraper import Level1Scraper
from level2_scraper import Level2Scraper

def test_complete_workflow():
    """测试完整工作流程"""
    print("🚀 开始测试完整工作流程...")
    
    target_url = "https://events.baidu.com/search/vein?platform=pc&record_id=648521&query=%E4%B8%AD%E5%9B%BD%E4%BA%BA%E6%B0%91%E6%8A%97%E6%97%A5%E6%88%98%E4%BA%89%E6%9A%A8%E4%B8%96%E7%95%8C%E5%8F%8D%E6%B3%95%E8%A5%BF%E6%96%AF%E6%88%98%E4%BA%89%E8%83%9C%E5%88%A980%E5%91%A8%E5%B9%B4%E7%BA%AA%E5%BF%B5%E6%97%A5&srcid=50367"
    
    # 第一步：一级爬取
    print("\n📊 第一步：一级界面爬取...")
    scraper = Level1Scraper()
    
    try:
        # 爬取核心信息
        if scraper.scrape_core_info(target_url):
            print("✅ 核心信息爬取成功")
            
            # 爬取子事件
            if scraper.scrape_sub_events(target_url):
                print("✅ 子事件爬取成功")
                scraper.save_data()
                print("✅ 一级数据保存成功")
                
                # 显示摘要
                scraper.print_summary()
                
                # 第二步：二级评论爬取（限制前3个事件进行测试）
                print(f"\n📝 第二步：二级评论爬取（测试前3个事件）...")
                
                # 创建二级爬虫实例
                level2_scraper = Level2Scraper(scraper.core_info.get('core_event_name', ''))
                
                # 只测试前3个有链接的事件
                test_events = []
                for event in scraper.sub_events[:10]:  # 检查前10个事件
                    if event.get('link') and len(test_events) < 3:
                        test_events.append(event)
                
                if test_events:
                    print(f"测试事件数量: {len(test_events)}")
                    for i, event in enumerate(test_events):
                        print(f"  {i+1}. {event['title'][:50]}...")
                    
                    # 开始爬取评论
                    total_comments = level2_scraper.scrape_all_comments(test_events)
                    
                    # 显示摘要
                    level2_scraper.print_summary()
                    
                    # 关闭资源
                    level2_scraper.close()
                    
                    print(f"\n🎉 测试完成！")
                    print(f"📊 测试事件数: {len(test_events)}")
                    print(f"📊 获取评论数: {total_comments}")
                    
                    # 验证文件是否生成
                    verify_files(scraper.core_info.get('core_event_name', ''))
                    
                else:
                    print("❌ 没有找到有链接的测试事件")
                
            else:
                print("❌ 子事件爬取失败")
        else:
            print("❌ 核心信息爬取失败")
    
    finally:
        scraper.close()

def verify_files(core_event_name):
    """验证生成的文件"""
    print(f"\n📁 验证生成的文件...")
    
    # 检查JSON文件
    level1_file = 'data/level1_data.json'
    level2_file = 'data/level2_data.json'
    
    if os.path.exists(level1_file):
        with open(level1_file, 'r', encoding='utf-8') as f:
            level1_data = json.load(f)
        print(f"✅ {level1_file} - 子事件数: {len(level1_data.get('sub_events', []))}")
    else:
        print(f"❌ {level1_file} 不存在")
    
    if os.path.exists(level2_file):
        with open(level2_file, 'r', encoding='utf-8') as f:
            level2_data = json.load(f)
        print(f"✅ {level2_file} - 评论数: {len(level2_data.get('comments', []))}")
    else:
        print(f"❌ {level2_file} 不存在")
    
    # 检查Excel文件
    excel_file = f'data/{core_event_name}_评论数据.xlsx'
    if os.path.exists(excel_file):
        try:
            df = pd.read_excel(excel_file)
            print(f"✅ {excel_file} - 行数: {len(df)}")
            print(f"   列名: {list(df.columns)}")
        except Exception as e:
            print(f"❌ 读取 {excel_file} 失败: {e}")
    else:
        print(f"❌ {excel_file} 不存在")

if __name__ == "__main__":
    test_complete_workflow()
