<h1 align="center">psnv</h1>

同步 Pixiv 作品至本地

## 使用方法

> [!IMPORTANT]
> 需要安装 Poetry

- clone 本项目至要运行的服务器
- 运行 `poetry install`
- 将 `config.example.json` 改为 `config.json`
- 把 Pixiv 账号的 `refresh_token` 填入 `config.json`
- 根据需求修改配置项
- 把以下命令加入 crontab

```bash
# 每周日运行一次
0 0 * * 0 cd <repo path> && poetry run python main.py
```

## TODO
- [x] 关注画师的作品
- [ ] 收藏的作品
- [ ] 排行榜作品
- [x] 插画
- [ ] 漫画
- [ ] 小说


## 感谢
- https://github.com/upbit/pixivpy