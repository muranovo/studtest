#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import re
import json

def parse_test_page(url):
    """Парсит страницу с тестом и извлекает информацию"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Извлекаем информацию о тесте
        test_info = {
            'title': '',
            'subject': '',
            'price': '',
            'questions_count': '',
            'views': '',
            'purchases': '',
            'university': '',
            'uploaded_by': '',
            'last_result': '',
            'description': '',
            'questions': []
        }
        
        # Парсим заголовок
        title_elem = soup.find('h1')
        if title_elem:
            test_info['title'] = title_elem.text.strip()
        
        # Парсим информацию о тесте из таблицы или других элементов
        info_table = soup.find('table', class_='table')
        if info_table:
            rows = info_table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    label = cells[0].text.strip().lower()
                    value = cells[1].text.strip()
                    
                    if 'предмет' in label:
                        test_info['subject'] = value
                    elif 'цена' in label or 'стоимость' in label:
                        test_info['price'] = value
                    elif 'вопрос' in label:
                        test_info['questions_count'] = value
                    elif 'просмотр' in label:
                        test_info['views'] = value
                    elif 'покуп' in label:
                        test_info['purchases'] = value
                    elif 'вуз' in label or 'университет' in label:
                        test_info['university'] = value
                    elif 'пользователь' in label or 'загруз' in label:
                        test_info['uploaded_by'] = value
        
        # Парсим вопросы и ответы
        questions_section = soup.find_all(['div', 'section'], class_=re.compile('question|test-item|quiz'))
        
        if not questions_section:
            # Альтернативный поиск вопросов
            content_div = soup.find('div', class_='content') or soup.find('div', id='content')
            if content_div:
                # Ищем вопросы по паттернам
                text_content = content_div.get_text()
                questions_pattern = re.compile(r'(?:Вопрос\s*\d+|^\d+\.|^\d+\))', re.MULTILINE)
                
                # Разбираем текст на вопросы
                lines = text_content.split('\n')
                current_question = None
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Проверяем, является ли строка началом вопроса
                    if questions_pattern.match(line):
                        if current_question:
                            test_info['questions'].append(current_question)
                        current_question = {
                            'number': len(test_info['questions']) + 1,
                            'text': line,
                            'options': [],
                            'correct_answer': ''
                        }
                    elif current_question:
                        # Добавляем варианты ответов или правильный ответ
                        if line.startswith(('а)', 'б)', 'в)', 'г)', 'д)', 'a)', 'b)', 'c)', 'd)', 'e)')):
                            current_question['options'].append(line)
                        elif 'правильн' in line.lower() or 'ответ:' in line.lower():
                            current_question['correct_answer'] = line
                        elif len(line) > 10:  # Продолжение текста вопроса
                            current_question['text'] += ' ' + line
                
                if current_question:
                    test_info['questions'].append(current_question)
        
        return test_info
        
    except Exception as e:
        print(f"Ошибка при парсинге страницы: {e}")
        return None

def format_test_html(test_info):
    """Форматирует информацию о тесте в HTML"""
    
    html = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }}
        h1 {{
            text-align: center;
            font-size: 2em;
            margin-bottom: 10px;
        }}
        .test-info {{
            text-align: center;
            font-size: 0.9em;
            color: #666;
            margin-bottom: 30px;
        }}
        .test-info p {{
            margin: 5px 0;
        }}
        .description {{
            margin-bottom: 30px;
            padding: 15px;
            background-color: #f5f5f5;
            border-radius: 5px;
        }}
        .question {{
            margin-bottom: 25px;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        .question-number {{
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .options {{
            margin-left: 20px;
            list-style-type: none;
        }}
        .options li {{
            margin: 5px 0;
        }}
        .correct-answer {{
            margin-top: 10px;
            color: green;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    
    <div class="test-info">
        <p><strong>Предмет:</strong> {subject}</p>
        <p><strong>Стоимость:</strong> {price}</p>
        <p><strong>Количество вопросов:</strong> {questions_count}</p>
        <p><strong>Количество просмотров теста:</strong> {views}</p>
        <p><strong>Количество покупок теста:</strong> {purchases}</p>
        <p><strong>ВУЗ:</strong> {university}</p>
        <p><strong>Пользователь заливший этот тест:</strong> {uploaded_by}</p>
        <p><strong>Последний результат сдачи теста:</strong> {last_result}</p>
    </div>
    
    {description_section}
    
    <div class="questions">
        {questions_html}
    </div>
</body>
</html>
    """
    
    # Форматируем описание
    description_section = ""
    if test_info.get('description'):
        description_section = f'<div class="description">{test_info["description"]}</div>'
    
    # Форматируем вопросы
    questions_html = ""
    for q in test_info.get('questions', []):
        options_html = ""
        for opt in q.get('options', []):
            options_html += f'<li>{opt}</li>'
        
        correct_answer_html = ""
        if q.get('correct_answer'):
            correct_answer_html = f'<div class="correct-answer">{q["correct_answer"]}</div>'
        
        questions_html += f"""
        <div class="question">
            <div class="question-number">Вопрос {q.get('number', '')}:</div>
            <div>{q.get('text', '')}</div>
            <ul class="options">
                {options_html}
            </ul>
            {correct_answer_html}
        </div>
        """
    
    # Заполняем шаблон
    return html.format(
        title=test_info.get('title', 'Тест'),
        subject=test_info.get('subject', 'Не указан'),
        price=test_info.get('price', 'Не указана'),
        questions_count=test_info.get('questions_count', 'Не указано'),
        views=test_info.get('views', 'Не указано'),
        purchases=test_info.get('purchases', 'Не указано'),
        university=test_info.get('university', 'Не указан'),
        uploaded_by=test_info.get('uploaded_by', 'Не указан'),
        last_result=test_info.get('last_result', 'Не указан'),
        description_section=description_section,
        questions_html=questions_html
    )

if __name__ == "__main__":
    url = "https://studizba.com/files/grazhdanskoe-pravo/answers/371660-grazhdanskoe-pravo-temy-1-12.html"
    
    print("Парсинг страницы...")
    test_info = parse_test_page(url)
    
    if test_info:
        # Сохраняем результат в HTML файл
        html_content = format_test_html(test_info)
        with open('test_formatted.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Сохраняем также в JSON для отладки
        with open('test_data.json', 'w', encoding='utf-8') as f:
            json.dump(test_info, f, ensure_ascii=False, indent=2)
        
        print("Парсинг завершен!")
        print(f"HTML файл сохранен: test_formatted.html")
        print(f"JSON данные сохранены: test_data.json")
    else:
        print("Не удалось распарсить страницу")