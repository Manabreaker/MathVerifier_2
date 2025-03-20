import json
from typing import Generator

from openai import OpenAI
import config
from logs import save_message
from tools import *

# Инициализация клиента OpenAI
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=config.github_token
)

# Основная функция для обработки запроса с использованием инструментов.
def run_with_tools(query: str, stream=False, model='gpt-4o') -> str or Generator:
    from config import messages

    # Сохраняем сообщение пользователя
    messages.append({"role": "user", "content": query})
    save_message("Пользователь", query)

    # Добавляем подсказки от RAG
    from rag import add_system_hints
    messages_with_hints = add_system_hints(messages.copy(), query)

    from config import tools

    response = client.chat.completions.create(
        model=model,
        messages=messages_with_hints,
        tools=tools,
        tool_choice="auto",
    )

    response_message = response.choices[0].message
    tool_calls = getattr(response_message, "tool_calls", None)

    if tool_calls:
        messages_with_hints.append(response_message)
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            tool_response = process_tool_call(function_name, function_args)

            messages_with_hints.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": tool_response
            })
            # Сохраняем информацию о вызове функции и ее результате
            save_message(role='###', content=response_message)
            save_message("Tool", f"Функция {function_name} с аргументами {function_args}. Результат: {tool_response}")

        second_response = client.chat.completions.create(
            model=model,
            messages=messages_with_hints
        )
        final_response = second_response.choices[0].message.content
        save_message("LLM", final_response)
        return final_response

    save_message("LLM", response_message.content)
    return response_message.content

def process_tool_call(function_name, function_args):
    """Обрабатывает вызов инструмента и возвращает результат."""
    if function_name == "execute_python_code":
        return execute_python_code(function_args.get("code"))
    elif function_name == "get_web_page":
        return get_web_page(function_args.get("url"))
    else:
        return json.dumps({"error": "Неизвестная функция"}, ensure_ascii=False)
