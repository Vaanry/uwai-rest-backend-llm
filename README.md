# FastAPI микросервис для интеграции с LLM


1. Клонируйте репозиторий:
    ```bash
    git clone git@github.com:uwai-rest/uwai-rest-backend-llm.git
    cd uwai-rest-backend-llm.git
    ```

2. Установите зависимости:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Для Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

3. Настройте переменные окружения в `.env` файле.
    ```env
    APP_TITLE = Your app title
    DATABASE_URL = Your database url
    OPENAI_API_KEY = Your openai api key
    HUGGINGFACEHUB_API_TOKEN = Your token  #  Если нет ключа OpenAI - возможно переключение на opensource модель
    FILES = Path to files folder #  Папка для хранения меню и прочих файлов, отправляемых клиенту
    ```
4. Запустите миграции базы данных с помощью Alembic:

    ```bash
    alembic upgrade head
    ```
    
5. Запустите FastAPI-приложение:
    ```bash
    uvicorn app.main:app --reload

    ```
## API Endpoints

### 1. `POST /chat`
Используется для общения с AI.

#### **Запрос**
**Метод:** `POST`  
**URL:** `/chat`  
**Content-Type:** `application/json`  
**Тело запроса:**
```json
{
  "id": "user123",
  "message": "Привет, расскажи о ресторане!"
}
