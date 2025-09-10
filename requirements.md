# 百度事件评论爬虫 - 需求说明

## 项目目标
爬取百度事件时间线页面及其子事件页面的评论数据，形成完整的闭环爬虫系统。

## 数据需求

### 一级界面（主时间线页面）
**目标URL**: `https://events.baidu.com/search/vein?platform=pc&record_id=648521&query=...`

**需要提取的数据**:
1. **核心事件名称**: `抗日战争暨反法西斯战争胜利80周年`
   - 来源: `<title>抗日战争暨反法西斯战争胜利80周年</title>`
2. **最新更新时间**: `更新至2025年9月5日 07:53`
   - 来源: `<p class="create-time">更新至2025年9月5日 07:53</p>`
3. **子事件数量**: `164`
   - 来源: `<span class="count">164</span>` 或页面中的事件项数量
4. **子事件列表**: 包含标题、时间、链接等信息
   - 来源: 页面中的 `.item` 元素

### 二级界面（子事件页面）
**目标**: 164个子事件对应的新闻页面

**需要提取的数据**（评论区）:
1. **用户ID**: `百度网友e041fff`
   - 来源: `<h5 class="user-bar-uname">百度网友e041fff</h5>`
2. **用户评论时间**: `09-04 10:16`
   - 来源: `<span class="time">09-04 10:16</span>`
3. **用户评论内容**: `在一点上，我与美国总统达成一致的观点。`
   - 来源: `<span class="type-text">在一点上，我与美国总统达成一致的观点。</span>`
4. **用户IP地址（地区）**: `江苏`
   - 来源: `<div class="area">江苏</div>`
5. **评论点赞数量**: `1706`
   - 来源: `<span class="like-text">1706</span>`

## 技术要求
- 使用Selenium处理动态内容
- 显示爬取进度
- 阶段性保存数据
- 合理的错误处理和重试机制
- 清晰的数据存储结构

## 输出格式
- JSON格式存储完整数据
- CSV格式便于分析
- 进度日志和错误日志

## 项目结构
```
pachong/
├── requirements.txt          # 依赖包
├── README.md               # 项目说明
├── requirements.md         # 需求说明（本文件）
├── main.py                # 主执行脚本
├── level1_scraper.py      # 一级界面爬虫
├── level2_scraper.py      # 二级界面爬虫
├── data_manager.py        # 数据管理和进度显示
└── data/                  # 数据存储目录
    ├── level1_data.json   # 一级界面数据
    ├── level2_data.json   # 二级界面数据
    └── combined_data.json  # 合并数据
```
