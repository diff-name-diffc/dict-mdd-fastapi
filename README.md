# MDD 资源查询 API

FastAPI 服务，用于查询 MDD 发音库中的音频和图片资源。

## 安装

```bash
uv sync
```

## 运行

```bash
uv run uvicorn app.main:app --reload --port 8000
```

## API 文档

访问 `http://localhost:8000/docs`

## API 端点

| 端点 | 说明 |
|------|------|
| `GET /api/v1/` | 服务状态 |
| `GET /api/v1/health` | 健康检查 |
| `GET /api/v1/resources/{word}` | 查询单词发音资源 |
| `GET /api/v1/resources/search/{pattern}` | 搜索资源键名 |

## 示例

```bash
# 查询 hello 的发音资源
curl http://localhost:8000/api/v1/resources/hello
```
