groq_api_key1 = "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"
groq_api_key2 = "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"
groq_api_key3 = "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"
github_token = "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"
messages = [
        {
            "role": "system",
            "content": (
                "Ты – профессиональный помощник, "
                "специализирующийся на проверке валидности доказательств теорем математического анализа. "
                "Твоя основная цель – внимательно и поэтапно анализировать представленные доводы, "
                "выявлять возможные ошибки и давать рекомендации по их исправлению. "
                "Если запрос неясен, содержит недостаточно информации или выходит за рамки твоей компетенции, "
                "вежливо сообщи пользователю, что не можешь его выполнить, "
                "и попроси уточнить или детализировать вопрос, чтобы дать наиболее точный и полезный ответ.\n"
                "Ты можешь использовать инструменты для выполнения задач. "
                "Например, писать Python-код, для проверки расчетов."
            )
        }
    ]

tools = [
        {
            "type": "function",
            "function": {
                "name": "execute_python_code",
                "description": "Запускает произвольный Python-код.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python-код, который нужно выполнить."
                        }
                    },
                    "required": ["code"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_web_page",
                "description": "Возвращает текстовое содержание веб-страницы, очищенное от HTML-тегов.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL веб-страницы, которую нужно прочитать."
                        }
                    },
                    "required": ["url"]
                }
            }
        }
    ]
