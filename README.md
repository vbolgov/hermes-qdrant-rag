# Hermes Qdrant RAG

Локальный RAG для Hermes Desktop: Qdrant в OrbStack, MLX embeddings на Apple Silicon, MCP-поиск и skills `rag_search` / `rag_update`.

## Поддерживаемая среда

- macOS 14+ на Apple Silicon;
- Hermes Agent Desktop;
- интернет на первом запуске для OrbStack, Python-пакетов, Qdrant image и MLX-модели.

## Запуск без команд пользователя

В новом чате Hermes Desktop отправь:

> Разверни Hermes Qdrant RAG из этого репозитория. Прочитай AGENTS.md и выполни `scripts/agent-bootstrap.sh`. Не индексируй документы без моего подтверждения.

Агент сам установит OrbStack при отсутствии, подготовит окружение, скачает MLX-модель, запустит Qdrant, подключит MCP и установит skills. После сообщения `READY` открой новый чат.

## Безопасная установка на машине с действующим RAG

Bootstrap создаёт links и конфигурацию относительно `HERMES_HOME`: `$HERMES_HOME/skills/...` и `$HERMES_HOME/.env`. Поэтому для теста или второго RAG используй отдельный Hermes profile / отдельный `HERMES_HOME`; он не изменит skills и `RAG_PROJECT_DIR` основного профиля. Обычная установка в текущий профиль использует путь самого clone как `$ROOT`, а не путь автора репозитория.

## Первый индекс и поиск

1. Положи личные документы в `library/` или задай другой локальный `RAG_DATA_DIR`.
2. В Hermes вызови `/skill rag_update`; изучи план и подтверди индексацию.
3. Для вопросов вызывай `/skill rag_search`.

`rag_search` всегда проверяет свежесть индекса. OCR, удаление векторов и rebuild требуют отдельного явного подтверждения.

## Публичный репозиторий и личные данные

В Git включены только нейтральные fixtures в `library/demo/` и `library/test-formats/`. `.env`, manifest, векторная база, кеш моделей и личные документы игнорируются. Не добавляй личные файлы обходом `.gitignore`.

## Компоненты

- `scripts/agent-bootstrap.sh` — единственная точка agent-first развёртывания;
- `scripts/warm_embedding_model.py` — скачивание и проверка embedding-модели;
- `ingest.py` — извлечение, chunking и синхронизация Qdrant;
- `rag_mcp.py` — MCP-инструменты поиска;
- `skills/` — RAG-навыки для Hermes;
- `docs/` — архитектура и диагностика.

## Проверка готовности

Bootstrap обязан завершить без ошибок:

- `docker info` доступен;
- Qdrant запущен;
- MLX возвращает вектор;
- тесты проходят;
- `ingest.py --dry-run --json` возвращает план;
- MCP `qdrant-rag` зарегистрирован.

Подробные правила для агента — в `AGENTS.md`.
