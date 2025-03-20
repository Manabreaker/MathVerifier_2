import datetime

def save_message(role, content):
    """Сохраняет сообщение в файл logs.txt с отметкой времени."""
    with open("logs.txt", "a", encoding="utf-8") as f:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{timestamp} - {role}: {content}\n")