# H3 Hexagon API Service

## Описание
FastAPI-сервис для работы с географическими данными через H3-гексагоны. Предоставляет API для пространственных запросов и агрегации данных.

## Установка

### Требования
- Python 3.8+
- Poetry (менеджер зависимостей)

### Инструкция

Клонируйте репозиторий:
git clone https://github.com/yourusername/h3-hexagon-api.git
cd h3-hexagon-api
poetry run uvicorn main:app --reload

1. Получение дочерних ячеек
GET /hex?parent_hex={h3_index}

Пример:
curl "http://localhost:8000/hex?parent_hex=8a194ab702b7fff"

2. Поиск в полигоне
GET /bbox?border=lat1/lon1,lat2/lon2,...
Пример:

curl "http://localhost:8000/bbox?border=56.0/38.0,56.1/38.0,56.1/38.1"

3. Агрегированные данные
GET /avg?resolution={level}
Пример:

curl "http://localhost:8000/avg?resolution=5"