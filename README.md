# Foodgram

## Описание проекта

Foodgram - это веб-приложение для создания кулинарных рецептов,
сохранения избранных рецептов и создания списка покупок на основе рецептов добавленных в корзину.
Проект  развернут на домене `foodgram-corp.ddns.net`, по адресу: https://foodgram-corp.ddns.net.

### Инструкция как развернуть проект в докере

1. Убедитесь, что у вас установлен Docker и Docker Compose.
2. Склонируйте репозиторий:

```
git clone https://github.com/StepanovDVP/foodgram.git
```

3. Перейдите в директорию проекта командой:

```
cd foodgram
```

4. Создайте файл `.env` и установите необходимые переменные окружения (см. пример ниже).
5. Запустите контейнеры:

```
docker compose up -d --build
```

6. Примените миграции:

```
docker compose exec backend python manage.py migrate
```

7. Создайте суперпользователя:

```
docker compose exec backend python manage.py createsuperuser
```

8. Приложение доступно по адресу: http://localhost:8000/
9. Пример файла `.env`:

```dotenv
POSTGRES_USER=django_user
POSTGRES_PASSWORD=mysecretpassword
POSTGRES_DB=django

DB_HOST=db
DB_PORT=5432

USE_SQLITE=False
SECRET_KEY=your_secret_key_here
DEBUG=False
ALLOWED_HOSTS=your_allowed_hosts_here
```

10. Для наполнения базы данных начальными данными используйте команду
```
docker compose exec backend python manage.py import_ingredients data/ingredients.json
```
### Пример запросов/ответов

Получение списка рецептов <br>
Запрос:
GET http://localhost:8000/api/recipes/ <br>
Ответ:

```
{
  "count": 123,
  "next": "http://foodgram-corp.ddns.net/api/recipes/?page=4",
  "previous": "http://foodgram-corp.ddns.net/api/recipes/?page=2",
  "results": [
    {
      "id": 1,
      "tags": [
        {
          "id": 1,
          "name": "Завтрак",
          "slug": "breakfast"
        }
      ],
      "author": {
        "email": "first@example.com",
        "id": 0,
        "username": "first",
        "first_name": "first",
        "last_name": "first",
        "is_subscribed": false,
        "avatar": "http://foodgram-corp.ddns.net/media/avatars/image.png"
      },
      "ingredients": [
        {
          "id": 1,
          "name": "Картофель отварной",
          "measurement_unit": "г",
          "amount": 10
        }
      ],
      "is_favorited": true,
      "is_in_shopping_cart": true,
      "name": "string",
      "image": "http://foodgram-corp.ddns.net/media/avatars/image.png",
      "text": "string",
      "cooking_time": 1
    }
  ]
}
```

Получение  подписок пользователя <br>
Запрос:
GET http://localhost/api/users/subscriptions/ <br>
Ответ:

```
{
  "count": 123,
  "next": "http://foodgram-corp.ddns.net/api/users/subscriptions/?page=4",
  "previous": "http://foodgram-corp.ddns.net/api/users/subscriptions/?page=2",
  "results": [
    {
      "email": "second@example.com",
      "id": 0,
      "username": "second",
      "first_name": "second",
      "last_name": "second",
      "is_subscribed": true,
      "recipes": [
        {
          "id": 0,
          "name": "string",
          "image": "http://foodgram-corp.ddns.net/media/recipes/image.png",
          "cooking_time": 1
        }
      ],
      "recipes_count": 1,
      "avatar": "http://foodgram-corp.ddns.net/media/avatars/image.png"
    }
  ]
}
```

## Стек технологий

* Django
* Django REST Framework
* PostgreSQL
* Docker, Docker Compose

### ДОКУМЕНТАЦИЯ

Находясь в папке infra проекта Foodgram, выполните команду docker-compose up. <br>
по адресу http://localhost/api/docs/ — спецификация к API.

#### Разработка Backend-приложения: Степанов Дмитрий Yandex Practicum 2024 
##### GitHub - StepanovDVP
##### DockerHub - dmitrystepanov24