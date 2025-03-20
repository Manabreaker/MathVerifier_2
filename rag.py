import json
import re
import os
from difflib import SequenceMatcher
from logs import save_message
from tools import *

# Словарь с подсказками для разных категорий запросов
TOOL_HINTS = {
    "python_code": {
        "keywords": ["напиши", "скрипт", "открой", "запусти", "включи", "код", "выполни", "python"],
        "hint": "функция execute_python_code позволяет выполнять Python-код. Ты можешь использовать эту функцию для запуска программного кода."
    },
    "web_content": {
        "keywords": ["содерж", "контент", "страниц", "текст"],
        "hint": "функция get_web_page позволяет получить текстовое содержимое веб-страницы по заданному URL."
    },
}

# Директория с описаниями теорем
THEOREMS_DIR = "theorems"


def load_theorems():
    """
    Загружает список теорем, обнаруживая файлы в каталоге THEOREMS_DIR.

    Возвращает:
        list: список названий теорем, полученных из имён файлов.
    """
    if not os.path.exists(THEOREMS_DIR):
        save_message("GAP", f"Каталог с теоремами не найден: {THEOREMS_DIR}")
        return []

    try:
        files = [f for f in os.listdir(THEOREMS_DIR) if f.endswith(".txt")]
        # Извлекаем название теоремы из имени файла: удаляем расширение и заменяем символы подчёркивания на пробелы
        theorems = [os.path.splitext(f)[0].replace('_', ' ').strip() for f in files if
                    len(os.path.splitext(f)[0].strip()) > 1]
        return theorems
    except Exception as e:
        save_message("GAP", f"Ошибка при загрузке списка теорем: {str(e)}")
        return []


def find_similar_theorem(query, threshold=0.2):
    """
    Находит теорему, наиболее похожую на запрос пользователя,
    перебирая все найденные файлы в каталоге THEOREMS_DIR.

    Args:
        query: строка с запросом пользователя.
        threshold: минимальный порог схожести (от 0 до 1).

    Returns:
        str или None: название наиболее похожей теоремы или None, если подходящая не найдена.
    """
    theorems = load_theorems()
    if not theorems:
        return None

    clean_query = query.lower()
    best_match = None
    best_score = 0

    for theorem in theorems:
        score = SequenceMatcher(None, clean_query, theorem.lower()).ratio()
        if score > best_score and score >= threshold:
            best_score = score
            best_match = theorem

    if best_match:
        save_message("GAP", f"Найдена похожая теорема: {best_match} (схожесть: {best_score:.2f})")
    return best_match


def get_theorem_content(theorem_name):
    """
    Получает содержимое файла теоремы.

    Args:
        theorem_name: название теоремы.

    Returns:
        str: содержимое файла с теоремой или пустая строка, если файл не найден.
    """
    # Формируем имя файла на основе названия теоремы: приводим к нижнему регистру, заменяем пробелы на подчёркивания
    filename = os.path.join(THEOREMS_DIR, f"{theorem_name.lower().replace(' ', '_')}.txt")

    if not os.path.exists(filename):
        save_message("GAP", f"Файл с теоремой не найден: {filename}")
        return ""

    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()

        # Ограничиваем размер контекста, если он слишком большой
        if len(content) > 2000:
            content = content[:2000] + "... (текст сокращен)"

        save_message("GAP", f"Загружено содержимое теоремы: {theorem_name}")
        return content
    except Exception as e:
        save_message("GAP", f"Ошибка при чтении файла теоремы: {str(e)}")
        return ""


def get_hints_for_query(query):
    """
    Анализирует запрос пользователя и возвращает подходящие подсказки
    для нейросети.

    Args:
        query: строка с запросом пользователя.

    Returns:
        str: подсказка для нейросети или пустая строка.
    """
    query = query.lower()
    matching_hints = []

    for category, data in TOOL_HINTS.items():
        for keyword in data["keywords"]:
            # Поиск ключевых слов как отдельных слов с помощью регулярных выражений
            if re.search(rf'\b{re.escape(keyword.lower())}\b', query):
                matching_hints.append(data["hint"])
                break  # Избегаем дублирования подсказок для одной категории

    if matching_hints:
        save_message("GAP", f"Подсказки для запроса: {', '.join(matching_hints)}")
        return "\n\n".join(matching_hints)

    return ""


def add_system_hints(messages, query):
    """
    Добавляет системные подсказки в список сообщений перед отправкой запроса нейросети.
    Реализует механизм Retrieval Augmented Generation (RAG), добавляя контекст из найденной теоремы.

    Args:
        messages: список сообщений для отправки нейросети.
        query: оригинальный запрос пользователя.

    Returns:
        list: обновлённый список сообщений с добавленными подсказками.
    """
    hints = get_hints_for_query(query)

    # Ищем теорему, наиболее похожую на запрос
    similar_theorem = find_similar_theorem(query)
    if similar_theorem:
        theorem_content = get_theorem_content(similar_theorem)
        if theorem_content:
            theorem_hint = f"Запрос пользователя похож на теорему '{similar_theorem}'. Вот информация о ней:\n\n{theorem_content}\n\n"
            hints = theorem_hint + (hints if hints else "")

    if hints:
        if messages and messages[0]["role"] == "system":
            original_content = messages[0]["content"]
            messages[0]["content"] = original_content + "\n\n" + hints
        else:
            messages.insert(0, {
                "role": "system",
                "content": hints
            })

    return messages
