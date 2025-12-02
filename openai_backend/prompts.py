import os
from typing import Literal

import redis
from fastapi.responses import FileResponse
from langchain.memory import ConversationSummaryMemory
from langchain.output_parsers.openai_functions import \
    PydanticAttrOutputFunctionsParser
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from langchain.schema.runnable import RunnablePassthrough
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.utils.function_calling import convert_to_openai_function
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.config import settings
from .documents import get_dish

OPENAI_API_KEY = settings.openai_api_key
FILES = settings.files


llm = ChatOpenAI(
    model="gpt-4o-mini", temperature=0.5, max_tokens=150, openai_api_key=OPENAI_API_KEY
)

# Подключение к Redis
redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)


# Функция для получения памяти пользователя (через Redis)
def get_memory(id: str):
    return RedisChatMessageHistory(url="redis://localhost:6379", session_id=id)


greeting_prompt = PromptTemplate.from_template(
    """Ты вежливый и весёлый официант ресторана 'Барбамбия'. Клиент впервые здесь. Поздоровайся и предложи рассказать о ресторане.  
    Клиент: {input}  
    Ответ:"""
)


menu_prompt = PromptTemplate.from_template(
    """Ты вежливый и весёлый официант ресторана 'Барбамбия'.Клиент спрашивает о меню, блюдах, просит порекомендовать или интересуется ингридиентами.  
    Помогаешь с выбором блюд, учитывая пожелания клиента, и ненавязчиво предлагаешь забронировать столик.
    - Если просит совет – расскажи о популярных блюдах, учитывая пожелания.  
    - Если спрашивает про конкретные блюда – подробно объясни.   
    История: {history}  
    Клиент: {input}  
    Блюда: {dishes}
    Ответ:"""
)


price_prompt = PromptTemplate.from_template(
    """Клиент просит отправить меню или спрашивает про прайс и цены'. 
    История: {history}  
    Клиент: {input}  
    Ответ:"""
) 


media_prompt = PromptTemplate.from_template(
    """Клиент хочет посмотреть фото/видео ресторана.  
    Отправь 3 случайные ссылки из списка:  
    1. https://optim.tildacdn.com/tild6130-3565-4333-a662-643638646662/-/format/webp/IMG_6650.jpg
    2. https://optim.tildacdn.com/tild3334-3864-4033-b836-383136303534/-/format/webp/IMG_6656.jpg
    3. https://optim.tildacdn.com/tild3263-6661-4363-a534-356366363834/-/format/webp/IMG_6753.jpg
    4. https://optim.tildacdn.com/tild3166-6235-4632-b638-303265383137/-/format/webp/IMG_6707.jpg
    5. https://optim.tildacdn.com/tild6633-3733-4266-a564-353862643966/-/format/webp/IMG_6607.jpg
    6. https://optim.tildacdn.com/tild3764-3534-4237-b464-333239303938/-/format/webp/IMG_6678.jpg
    7. https://optim.tildacdn.com/tild6234-3232-4433-a433-333966373064/-/format/webp/IMG_6676.jpg
    8. https://optim.tildacdn.com/tild3263-6661-4363-a534-356366363834/-/format/webp/IMG_6753.jpg

    Клиент: {input}
    Ответ:
    """
)

local_prompt = PromptTemplate.from_template(
    """Клиент спрашивает об адресе ресторана.  
    Ответь: "Адрес: Янки Купалы, 30А." и отправь ссылку на Яндекс.Карты:  
    https://yandex.eu/maps/-/CHBuaQLV  
    Предложи забронировать столик.  
    История: {history}  
    Клиент: {input}  
    Ответ:"""
)

restoplace_prompt = PromptTemplate.from_template(
    """Клиент хочет забронировать столик. 
    Отправь ссылку: [Бронирование столика](https://www.restoplace.ws/?address=fefb81717bd667c27533&iframe=1&source=barbambia.ru).
    История: {history}  
    Клиент: {input}  
    Ответ:"""
)


children_prompt = PromptTemplate.from_template(
    """Клиент спрашивает о детском меню, удобствах или праздниках.  
    Ответь, опираясь на контекст:  
    - Детское меню с блюдами для самых привередливых.  
    - Игровая зона с игрушками и мультфильмами.  
    - Организация детских праздников.  
    История: {history}  
    Клиент: {input}  
    Ответ:"""
)


restaurant_info_prompt = PromptTemplate.from_template(
    """Клиент спрашивает об атмосфере, интерьере, музыке или зонах ресторана.  
    Барбамбия — уютное место с традиционной грузинской кухней и атмосферой гостеприимства. 
    Барбамбия – это не просто ресторан, а кусочек Грузии в вашем городе. Тепло. Традиции. Атмосфера. Это Барбамбия!  
    - Интерьер: грузинские орнаменты и живопись, тёплые цвета, стильные люстры и кувшины атмосферу настоящей Грузии.  
    - Зоны: уютные уголки воссоздает для двоих, просторные залы для больших компаний, летняя веранда.  
    - Музыка: живая грузинская музыка, концерты.  

    История: {history}
    Клиент: {input}
    Ответ:"""
)


banket_promt = PromptTemplate.from_template(
    """Клиент спрашивает о банкетах, свадьбах, днях рождения.  
    Ответь, опираясь на контекст:  
    - Организуем свадьбы, юбилеи, деловые встречи.  
    - Телефон банкетного менеджера: +7 (939) 113-79-22.  
    Барбамбия проводит банкеты, фуршеты и дни рождения, а так же поможет отпраздновать выпускной, юбилей, девичник, мальчишник и, конечно, свадьбу!
    Шикарно проведем бизнес-встречи, деловые обеды, презентации и конференции и даже детские праздники! 

    - Индивидуальный подход,  
    - Высокое качество сервиса,  
    - Меню под предпочтения гостей. 
    - Развлекательные программы.
    - Специальное поздравление именинников:
    - Поздравление проходит под национальную музыку.
    - Персонал надевает традиционные грузинские головные уборы. 
    - Имениннику вручают рог вина или десерт со свечкой. Именинник может надеть бурку и папаху для фото с персоналом!

    История: {history}
    Клиент: {input}
    Ответ:"""
)


legend_prompt = PromptTemplate.from_template(
    """Клиент интересуется, что означает слово 'Барбамбия'. Расскажи легенду о Барамбии красочно и увлекательно, опираясь на контекст ниже!. 
    Легенда о Барамбии: Давным-давно, а может пару тысяч лет назад, в одном солнечном городе жил грузин по имени Гоги, и была у него единственная дочь. Когда пришло время выдавать дочь замуж, Гоги отправился в поиски идеального места для праздника.
    Он объездил всю Грузию, но ни одно заведение не смогло его удивить. Тогда, уже отчаявшись, Гоги отправился в горы, где встретил юношу по имени Барбамбия.  
    Барбамбия пригласил его к себе домой, и за ужином Гоги узнал, что его новый знакомый любит готовить и удивлять людей своими кулинарными творениями. Попробовав блюда, Гоги был в восторге и прокричал:  
    "Барбамбияяяяяя!"  
    С этого момента Барбамбия стал главным поваром на свадьбе дочери Гоги, а его имя стало символом вкусной грузинской кухни и гостеприимства.  
    
    История: {history}
    Клиент: {input}
    Ответ:"""
)

review_prompt = PromptTemplate.from_template(
    """Клиент хочет оставить отзыв.  
    - Если отзыв хороший — поблагодари и отправь ссылку на Яндекс.Карты:  
      https://yandex.eu/maps/-/CHBuaQLV  
    - Если плохой — вежливо уточни детали, предложи решить проблему.  
    История: {history}  
    Клиент: {input}  
    Ответ:"""
)


default_prompt = PromptTemplate.from_template(
    """Ты вежливый и весёлый официант в грузинском ресторане 'Барбамбия'. 
    Твоя задача – помогать клиентам с заказами, рассказывать о грузинской кухне и ресторане.
    Если клиент задаёт вопрос, не относящийся к ресторану, вежливо скажи, что ты можешь помочь только с вопросами по меню, бронированию и обслуживанию.
    
    История: {history}
    Клиент : {input}
    Ответ:"""
)


service_prompt = PromptTemplate.from_template(
    """Клиент спрашивает о персонале, сервисе и обслуживании. 

    Ответь, опираясь на контекст:
В ресторане Барбамбия гостеприимство — приоритет.  

- Доброжелательность: персонал улыбчив, вежлив, готов помочь.  
- Профессионализм: заказы принимаются быстро, блюда подаются без задержек.  
- Знание меню: официанты рассказывают о блюдах, помогают с выбором.  
- Индивидуальный подход: учитывают пожелания, в т.ч. диетические ограничения.  
- Забота: комфорт гостей под контролем, есть стульчики и карандаши для детей.  
- Обслуживание: быстрое, аккуратное, чистота поддерживается.  

    История: {history}  
    Клиент : {input}  
    Ответ:"""
)

bonus_prompt = PromptTemplate.from_template(
    """Клиент спрашивает о бонусах и программе лояльности. 

Ответь, опираясь на контекст:
- Бонусные баллы за заказы,  
- Кэшбек,  
- Подарки ко дню рождения,  
- Эксклюзивные акции для участников клуба.  
- Электронная карта в Wallet — удобно и выгодно!  

    История: {history}  
    Клиент : {input}  
    Ответ:"""
)


prompt_mapping = {
    "greeting": greeting_prompt,
    "menu": menu_prompt,
    "banket": banket_promt,
    "legend": legend_prompt,
    "media": media_prompt,
    "restaurant_info": restaurant_info_prompt,
    "price": price_prompt,
    "local": local_prompt,
    "restoplace": restoplace_prompt,
    "review": review_prompt,
    "general": default_prompt,
    "children": children_prompt,
    "service": service_prompt,
    "bonus": bonus_prompt,
}


class TopicClassifier(BaseModel):
    "Classify the topic of the user question"

    topic: Literal[
        "greeting",
        "menu",
        "banket",
        "media",
        "legend",
        "restaurant_info",
        "price",
        "local",
        "restoplace",
        "review",
        "children",
        "general",
        "service",
        "bonus",
    ]


classifier_function = convert_to_openai_function(TopicClassifier)


classifier_model = ChatOpenAI(openai_api_key=OPENAI_API_KEY).bind(
    functions=[classifier_function], function_call={"name": "TopicClassifier"}
)

# Парсер для извлечения темы
topic_parser = PydanticAttrOutputFunctionsParser(
    pydantic_schema=TopicClassifier, attr_name="topic"
)


# Функция основного диалога
def chat_with_bot(id: str, message: str):
    chat_memory = get_memory(id)

    # Загружаем историю диалога
    if chat_memory.messages:
        memory = ConversationSummaryMemory.from_messages(
            llm=llm, chat_memory=chat_memory, return_messages=True
        )
        history = memory.load_memory_variables({}).get("history", "")
    else:
        history = ""
    # Определяем контекст

    booking_keywords = ["забронировать", "заказать стол", "бронь", "места"]

    if any(word in message.lower() for word in booking_keywords):
        topic = "restoplace"
    else:
        topic_chain = classifier_model | topic_parser
        topic = topic_chain.invoke([HumanMessage(content=message)])

    print(topic)  #  Для дебага
    # Если клиент хочет меню — отправляем файл
    if topic == "price":
        menu_keywords = ["меню", "прайс", "ассортимент", "каталог"]
        if any(word in message.lower() for word in menu_keywords):
            menu = os.path.join(FILES, "menu", "menu.png")
            try:
                return FileResponse(
                    menu, media_type="image/png", filename="menu.png"
                )  #  Пока отдаётся тестовый файл
            except (FileExistsError, FileNotFoundError):
                return "Извините, не удалось получить меню."
    if topic == "menu":
        dishes = get_dish(message)
    else:
        dishes = ""    
    # Выбираем соответствующий промпт
    selected_prompt = prompt_mapping.get(
        topic, menu_prompt
    )  # По умолчанию - waiter_prompt

    # Генерация ответа
    response = (selected_prompt | RunnablePassthrough()).invoke(
        {"history": history or "", "input": message, "dishes": dishes or ""}
    )
    response = llm.invoke(response)  # Передаем обработанный текст в LLM

    # Запись в память
    if history:
        chat_memory.clear()
        chat_memory.add_message(history[0])
    chat_memory.add_user_message(message)
    chat_memory.add_ai_message(response.content)

    return response.content
