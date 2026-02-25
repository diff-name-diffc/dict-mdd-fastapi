# MDD 资源查询 API

FastAPI 服务，用于查询 MDD 发音库中的音频和图片资源。

## 安装

```bash
uv sync
```

## 运行

```bash
uv run uvicorn main:app --reload --port 8000
```

## 使用

访问 `http://localhost:8000/docs` 查看 API 文档。

### 查询单词资源

```
GET /resources/{word}
```

示例:
```
GET /resources/hello
```
