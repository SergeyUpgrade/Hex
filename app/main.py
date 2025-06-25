import random
from fastapi import FastAPI, HTTPException
import h3
from typing import List, Dict
import statistics

from shapely.geometry import Point, Polygon
from pydantic import BaseModel
from math import radians, sin, cos, sqrt, atan2

app = FastAPI()


# Модель для ответа API
class HexagonData(BaseModel):
    h3_index: str
    level: int
    cell_id: int


def haversine_distance(lat1, lon1, lat2, lon2):
    # Радиус Земли в километрах
    R = 6371.0

    # Переводим градусы в радианы
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Разница координат
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Формула гаверсинусов
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


def generate_initial_dataset() -> List[Dict]:
    """
    Создаем датасет
    :return:
    """
    center_lat, center_lon = 56.0, 38.0  # 56°N 38°E
    radius_km = 7
    resolution = 12

    center_hex = h3.latlng_to_cell(center_lat, center_lon, resolution)
    k_rings = int(radius_km / 0.5) + 1  # Эмпирическая оценка

    hexagons = h3.grid_disk(center_hex, k_rings)

    dataset = []
    for h3_index in hexagons:
        hex_lat, hex_lon = h3.cell_to_latlng(h3_index)
        distance = haversine_distance(center_lat, center_lon, hex_lat, hex_lon)

        if distance <= radius_km:
            dataset.append({
                "h3_index": h3_index,
                "level": random.randint(-120, -47),
                "cell_id": random.randint(1, 100)
            })

    return dataset


DATASET = generate_initial_dataset()


@app.get("/hex", response_model=List[HexagonData])
async def get_hex(parent_hex: str):
    try:
        if not h3.is_valid_cell(parent_hex):
            raise HTTPException(status_code=400, detail="Invalid H3 index")

        children = h3.cell_to_children(parent_hex, 12)
        result = [item for item in DATASET if item["h3_index"] in children]
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


#@app.get("/bbox", response_model=List[HexagonData])
#def filter_by_border(border: str):
#    """
#    Фильтрует датасет, оставляя только элементы, попадающие в заданные границы
#
#    Параметры:
#    dataset - исходный массив данных в формате [[h3_index, level, cell_id], ...]
#    border - строка с координатами границ в формате "lat1,lon1,lat2,lon2,...,latN,lonN"
#
#    Возвращает:
#    Отфильтрованный массив данных
#    """
#    # 1. Преобразуем border в список координат полигона
#    points = []
#    for pair in border.split(','):
#        lat, lon = map(float, pair.split('/'))
#        points.append((lon, lat))  # Shapely использует (x,y) = (lon,lat)
#
#    if len(points) < 3:
#        raise HTTPException(status_code=400, detail="Необходимо минимум 3 точки для полигона")
#
#    polygon = Polygon(points)
#
#    # 2. Фильтруем датасет
#    filtered_data = []
#    for item in DATASET:
#        h3_index = item[0]
#        lat, lon = h3.cell_to_latlng(h3_index)
#        point = Point(lon, lat)
#
#        if polygon.contains(point):
#            filtered_data.append(item)
#
#    return filtered_data


@app.get("/bbox", response_model=List[HexagonData])
async def get_bbox(border: str):
    """
    Возвращает элементы датасета, попадающие в заданный полигон.

    Параметры:
    - border: строка с координатами границы в формате 'lat1/lon1,lat2/lon2,...'
              Минимум 3 точки. Полигон автоматически замыкается.
    """
    try:
        # Парсинг координат
        points = []
        for point in border.split(','):
            try:
                lat, lon = map(float, point.strip().split('/'))
                points.append((lat, lon))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Неверный формат координат: '{point}'. Используйте 'широта/долгота'"
                )

        if len(points) < 3:
            raise HTTPException(
                status_code=400,
                detail="Для формирования полигона требуется минимум 3 точки"
            )

        # Замыкаем полигон
        if points[0] != points[-1]:
            points.append(points[0])

        # Создаем правильную структуру полигона для H3
        # Вариант 1: Для новых версий H3 (4.x+)
        geo_json_polygon = {
            "type": "Polygon",
            "coordinates": [[[lon, lat] for lat, lon in points]]
        }

        # Получаем гексагоны (используем правильный метод для вашей версии)
        hexagons = h3.polygon_to_cells(geo_json_polygon, 12)  # Для H3 v4.x

        # Фильтруем датасет
        result = [item for item in DATASET if item["h3_index"] in hexagons]

        return result

    except Exception as e:
        #print("Points:", points)
        #print("Polygon:", geo_json_polygon)
        #print("Hexagons found:", len(hexagons))
        raise HTTPException(
            status_code=400,
            detail=f"Ошибка обработки запроса: {str(e)}"
        )


@app.get("/avg")
async def get_avg(resolution: int):
    try:
        if resolution < 0 or resolution > 12:
            raise HTTPException(status_code=400, detail="Resolution must be between 0 and 12")

        grouped_data = {}
        for item in DATASET:
            parent_hex = h3.cell_to_parent(item["h3_index"], resolution)
            key = (parent_hex, item["cell_id"])
            if key not in grouped_data:
                grouped_data[key] = []
            grouped_data[key].append(item["level"])

        result = []
        for (parent_hex, cell_id), levels in grouped_data.items():
            result.append({
                "h3_index": parent_hex,
                "cell_id": cell_id,
                "median_level": int(statistics.median(levels))
            })

        # Сортировка по cell_id
        result.sort(key=lambda x: x["cell_id"])

        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
