# NetScope

Веб-приложение для базовой сетевой диагностики. Можно проверить DNS-записи домена, узнать какие порты открыты на хосте, и посмотреть HTTP-заголовки любого сайта — всё это прямо в браузере, без установки дополнительных программ.

Сделано в рамках учебного проекта по компьютерным сетям.

**Ссылка:** https://netscope-c4fb.onrender.com  
**Документация:** https://netscope-c4fb.onrender.com/docs.html

## Что умеет

| Инструмент | Описание |
|---|---|
| DNS-запрос | Получить A, AAAA, MX, NS, TXT-записи домена |
| Сканер портов | Проверить TCP-порты на доступность (до 20 штук) |
| HTTP-заголовки | Посмотреть заголовки ответа сервера |

## Технологии

- Бэкенд: Python, FastAPI
- Фронтенд: HTML, CSS, JavaScript (без фреймворков)
- Контейнеризация: Docker, Docker Compose
- Обратный прокси: Caddy (автоматический HTTPS через Let's Encrypt)
- Хостинг: Render

## Запуск локально

Нужен Docker и Docker Compose.

```bash
git clone https://github.com/McMaxim/netscope.git
cd netscope
docker compose up -d
```

После этого приложение будет доступно на http://localhost:8000

Для работы с HTTPS на своём домене нужно поменять `yourdomain.com` в файле `Caddyfile` на свой домен и запустить через `docker compose up -d` на сервере с открытыми портами 80 и 443.

## Структура проекта

```
netscope/
├── backend/
│   ├── main.py          # FastAPI приложение, все эндпоинты
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html       # Главная страница
│   └── docs.html        # Документация
├── Dockerfile           # Основной Dockerfile (для Render)
├── docker-compose.yml   # Для локального запуска с Caddy
├── Caddyfile            # Конфиг Caddy с автоматическим HTTPS
└── render.yaml          # Конфиг для деплоя на Render
```

## API

Все эндпоинты принимают POST-запрос с JSON и возвращают JSON.

```
POST /api/dns        {"host": "google.com"}
POST /api/ports      {"host": "1.1.1.1", "ports": [80, 443]}
POST /api/headers    {"url": "https://example.com"}
GET  /api/health
```

## Лицензия

MIT
