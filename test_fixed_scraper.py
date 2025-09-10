#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的爬虫
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from level1_scraper import Level1Scraper
from level2_scraper import Level2Scraper
from data_manager import DataManager
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_scraper.log', encoding='utf-8')
    ]
)

def test_scraper():
    """测试修复后的爬虫"""
    logger = logging.getLogger(__name__)
    
    # 测试URL
    test_url = "https://events.baidu.com/search/vein?platform=pc&record_id=648521&query=%E4%B8%AD%E5%9B%BD%E4%BA%BA%E6%B0%91%E6%8A%97%E6%97%A5%E6%88%98%E4%BA%89%E6%9A%A8%E4%B8%96%E7%95%8C%E5%8F%8D%E6%B3%95%E8%A5%BF%E6%96%AF%E6%88%98%E4%BA%89%E8%83%9C%E5%88%A980%E5%91%A8%E5%B9%B4%E7%BA%AA%E5%BF%B5%E6%97%A5&srcid=50367"
    
    try:
        # 初始化爬虫
        logger.info("初始化爬虫...")
        scraper1 = Level1Scraper()
        scraper2 = Level2Scraper()
        
        # 测试核心信息爬取
        logger.info("测试核心信息爬取...")
        if scraper1.scrape_core_info(test_url):
            logger.info("✅ 核心信息爬取成功")
            logger.info(f"核心信息: {scraper1.core_info}")
        else:
            logger.error("❌ 核心信息爬取失败")
            return False
        
        # 测试子事件爬取（限制数量进行快速测试）
        logger.info("测试子事件爬取（限制前5个）...")
        if scraper1.scrape_sub_events(test_url):
            logger.info(f"✅ 子事件爬取成功，共找到 {len(scraper1.sub_events)} 个子事件")
            
            # 显示前5个子事件
            for i, event in enumerate(scraper1.sub_events[:5]):
                logger.info(f"  子事件 {i+1}: {event.get('title', 'N/A')}")
        else:
            logger.error("❌ 子事件爬取失败")
            return False
        
        # 测试评论爬取（只测试第一个子事件）
        if scraper1.sub_events:
            logger.info("测试评论爬取（第一个子事件）...")
            first_event = scraper1.sub_events[0]
            event_url = first_event.get('url')
            
            if event_url:
                logger.info(f"测试URL: {event_url}")
                comments = scraper2.scrape_comments(event_url, first_event.get('title', ''), first_event.get('id', ''))
                
                if comments:
                    logger.info(f"✅ 评论爬取成功，共找到 {len(comments)} 条评论")
                    
                    # 显示前3条评论
                    for i, comment in enumerate(comments[:3]):
                        logger.info(f"  评论 {i+1}: {comment.get('comment_content', 'N/A')[:50]}...")
                else:
                    logger.warning("⚠️ 未找到评论")
            else:
                logger.warning("⚠️ 第一个子事件没有URL")
        
        logger.info("🎉 测试完成！")
        return True
        
    except Exception as e:
        logger.error(f"测试过程中出现错误: {e}")
        return False
    
    finally:
        # 清理资源
        try:
            scraper1.close()
            scraper2.close()
        except:
            pass

if __name__ == "__main__":
    success = test_scraper()
    if success:
        print("\n✅ 测试成功！爬虫修复有效。")
    else:
        print("\n❌ 测试失败！需要进一步调试。")
