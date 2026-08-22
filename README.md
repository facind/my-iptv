# my-iptv

自动抓取 iptv-org 多个上游（主列表/亚洲区/新闻/香港/纪录片/电影），按频道分组（香港台/HBO/Discovery/NGC/新闻/其他），URL 去重后并发测速（超时 8s 的链直接丢弃），每天北京 06:00 自动更新 `my.m3u`。

## 播放器订阅链

- raw：`https://raw.githubusercontent.com/<你的用户名>/my-iptv/main/my.m3u`
- CDN（国内更稳）：`https://cdn.jsdelivr.net/gh/<你的用户名>/my-iptv@main/my.m3u`
