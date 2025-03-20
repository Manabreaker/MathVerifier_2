import ast
import requests
from bs4 import BeautifulSoup
import speech_recognition as sr
import subprocess
import sys
import os
import json
from logs import save_message

def get_imports(code: str) -> list:
    """
    Парсит код и возвращает список импортируемых модулей.
    """
    tree = ast.parse(code)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split('.')[0])
    return list(imports)

def check_and_install_modules(code):
    """
    Проверяет наличие импортов в коде, устанавливает недостающие библиотеки
    и добавляет их в requirements.txt.

    Args:
        code: строка с Python-кодом

    Returns:
        dict: словарь с результатом проверки и установки
    """

    # Определяем, какие библиотеки нужно установить
    to_install = get_imports(code)
    # Если нет библиотек для установки, возвращаем исходный код
    if not to_install:
        return {"status": "success", "code": code, "installed": []}

    # Устанавливаем недостающие библиотеки
    installed = []
    for module in to_install:
        try:
            save_message("GAP", f"Установка библиотеки: {module}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", module])
            installed.append(module)
        except subprocess.CalledProcessError as e:
            return {
                "status": "error",
                "message": f"Ошибка при установке библиотеки {module}: {str(e)}",
                "installed": installed
            }

    # Добавляем библиотеки в requirements.txt
    if installed:
        current_requirements = set()
        if os.path.exists("requirements.txt"):
            with open("requirements.txt", "r") as f:
                current_requirements = {line.strip() for line in f if line.strip()}

        with open("requirements.txt", "a") as f:
            for module in installed:
                if module not in current_requirements:
                    f.write(f"{module}\n")

        save_message("GAP", f"Библиотеки {', '.join(installed)} добавлены в requirements.txt")

    return {"status": "success", "code": code, "installed": installed}

def execute_python_code(code):
    """
    Проверяет и устанавливает необходимые библиотеки, затем выполняет Python-код.

    Args:
        code: строка с Python-кодом для выполнения

    Returns:
        str: JSON-строка с результатом выполнения
    """

    check_result = check_and_install_modules(code)

    # Если произошла ошибка при установке модулей, возвращаем её
    if check_result["status"] == "error":
        return json.dumps(check_result, ensure_ascii=False)

    # Если были установлены новые библиотеки, сообщим об этом
    installed_modules = check_result.get("installed", [])

    try:
        import contextlib
        import io
        # Создаем объект для перехвата stdout
        output_capture = io.StringIO()
        local_vars = {}

        # Выполняем код с перехватом вывода
        with contextlib.redirect_stdout(output_capture):
            exec(code, globals(), local_vars)

        # Получаем захваченный вывод
        output = output_capture.getvalue()

        # Собираем значения переменных (кроме служебных)
        variables = {k: repr(v) for k, v in local_vars.items()
                     if not k.startswith('_')}

        result = {
            "status": "success",
            "output": output if output else None,
            "variables": variables if variables else None,
            "result": "Код запущен успешно"
        }

        # Если были установлены библиотеки, добавляем эту информацию
        if installed_modules:
            result["installed_modules"] = installed_modules
            result["message"] = f"Были автоматически установлены библиотеки: {', '.join(installed_modules)}"

    except Exception as e:
        result = {
            "status": "error",
            "message": str(e)
        }

    return json.dumps(result, ensure_ascii=False)

def get_web_page(url):
    """
    Получает содержимое веб-страницы по заданному URL и возвращает её текстовое содержимое.

    Использует BeautifulSoup для удаления HTML-тегов, возвращая только чистый текст.
    Если возникает ошибка, возвращает сообщение об ошибке.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # вызывает исключение, если статус не 200
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text(strip=True)
        return text.replace("\n", " ").replace("\r", "").replace("\t", "").replace("  ", " ")
    except Exception as e:
        return f"Error: {str(e)}"

def recognize_speech():
    """Распознаёт голос и выводит текст"""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Говорите...")
        recognizer.adjust_for_ambient_noise(source)  # Подстройка под шум
        audio = recognizer.listen(source)  # Запись звука

    try:
        text = recognizer.recognize_google(audio, language="ru-RU")  # Google STT
        print(f"Вы сказали: {text}")
        return json.dumps({"status": "success", "text": text}, ensure_ascii=False)
    except sr.UnknownValueError:
        print("Не удалось распознать речь")
        return json.dumps({"status": "error", "message": "Не удалось распознать речь"}, ensure_ascii=False)
    except sr.RequestError:
        print("Ошибка запроса к сервису Google")
        return json.dumps({"status": "error", "message": "Ошибка запроса к сервису Google"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)