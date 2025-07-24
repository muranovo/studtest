#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import re
import json

def parse_studizba_test(url):
    """Парсит страницу с тестом на studizba.com"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Извлекаем информацию о тесте
        test_info = {
            'title': '',
            'subject': 'Гражданское право',
            'price': '150 рублей',
            'questions_count': '',
            'views': '',
            'purchases': '',
            'university': 'МФПУ Синергия',
            'uploaded_by': '',
            'last_result': '',
            'description': '',
            'questions': []
        }
        
        # Парсим заголовок
        title_elem = soup.find('h1')
        if title_elem:
            test_info['title'] = title_elem.text.strip()
        
        # Ищем информацию в мета-данных страницы
        meta_info = soup.find_all('div', class_=['file-info', 'file-meta', 'info-block'])
        for info_block in meta_info:
            text = info_block.get_text()
            if 'просмотр' in text.lower():
                views_match = re.search(r'(\d+)\s*просмотр', text)
                if views_match:
                    test_info['views'] = views_match.group(1)
            if 'покуп' in text.lower() or 'продаж' in text.lower():
                purchases_match = re.search(r'(\d+)\s*(?:покуп|продаж)', text)
                if purchases_match:
                    test_info['purchases'] = purchases_match.group(1)
        
        # Парсим содержимое страницы для поиска вопросов
        content_area = soup.find('div', class_='file-content') or soup.find('div', class_='content-area') or soup.find('article') or soup.body
        
        if content_area:
            # Извлекаем весь текст
            full_text = content_area.get_text(separator='\n')
            
            # Ищем количество вопросов
            questions_count_match = re.search(r'(\d+)\s*(?:вопрос|question)', full_text, re.IGNORECASE)
            if questions_count_match:
                test_info['questions_count'] = questions_count_match.group(1)
            
            # Ищем информацию о последнем результате
            result_patterns = [
                r'(?:сдан|результат).*?(\d+[,.]?\d*)\s*из\s*(\d+[,.]?\d*).*?(\d+%?)',
                r'результат.*?(\d+%)',
                r'(?:год|дата).*?(\d{4}[-/]\d{4}|\d{4})'
            ]
            
            for pattern in result_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    if 'из' in pattern:
                        test_info['last_result'] = f"Последний раз тест был сдан на результат {match.group(1)} из {match.group(2)} ({match.group(3)})"
                    break
            
            # Парсим вопросы и ответы
            # Разбиваем текст на строки
            lines = full_text.split('\n')
            
            current_question = None
            question_number = 0
            
            # Паттерны для определения вопросов
            question_patterns = [
                re.compile(r'^(?:Вопрос|Question)\s*(\d+)', re.IGNORECASE),
                re.compile(r'^(\d+)\s*[.)]'),
                re.compile(r'^(\d+)\s*(?:вопрос|question)', re.IGNORECASE)
            ]
            
            # Паттерны для вариантов ответов
            option_patterns = [
                re.compile(r'^[а-яa-z]\s*[.)]', re.IGNORECASE),
                re.compile(r'^[•\-\*]\s+'),
                re.compile(r'^\s*(?:Выберите один ответ:|Select one:|Варианты ответов?:)', re.IGNORECASE)
            ]
            
            # Паттерны для правильных ответов
            answer_patterns = [
                re.compile(r'(?:правильн|верн|correct|answer|ответ).*?[:]\s*(.+)', re.IGNORECASE),
                re.compile(r'^\+\s*(.+)'),  # Ответ, начинающийся с +
                re.compile(r'^✓\s*(.+)'),   # Ответ с галочкой
            ]
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                if not line:
                    i += 1
                    continue
                
                # Проверяем, является ли строка началом вопроса
                is_question = False
                for pattern in question_patterns:
                    match = pattern.match(line)
                    if match:
                        is_question = True
                        if current_question and (current_question['text'] or current_question['options']):
                            test_info['questions'].append(current_question)
                        
                        question_number += 1
                        current_question = {
                            'number': question_number,
                            'text': '',
                            'options': [],
                            'correct_answer': ''
                        }
                        
                        # Извлекаем текст вопроса
                        question_text = pattern.sub('', line).strip()
                        if question_text:
                            current_question['text'] = question_text
                        else:
                            # Текст вопроса может быть на следующей строке
                            if i + 1 < len(lines):
                                i += 1
                                current_question['text'] = lines[i].strip()
                        break
                
                if not is_question and current_question:
                    # Проверяем, является ли строка вариантом ответа
                    is_option = False
                    
                    # Проверка на стандартные варианты (а), б), в) и т.д.)
                    option_match = re.match(r'^([а-яa-z])\s*[.)]\s*(.+)', line, re.IGNORECASE)
                    if option_match:
                        current_question['options'].append(line)
                        is_option = True
                    else:
                        # Проверка других паттернов вариантов
                        for pattern in option_patterns:
                            if pattern.match(line):
                                current_question['options'].append(line)
                                is_option = True
                                break
                    
                    if not is_option:
                        # Проверяем, является ли строка правильным ответом
                        for pattern in answer_patterns:
                            match = pattern.search(line)
                            if match:
                                current_question['correct_answer'] = line
                                break
                        else:
                            # Если это не вариант и не ответ, возможно это продолжение текста вопроса
                            if not current_question['options'] and len(line) > 10:
                                current_question['text'] += ' ' + line
                
                i += 1
            
            # Добавляем последний вопрос
            if current_question and (current_question['text'] or current_question['options']):
                test_info['questions'].append(current_question)
        
        # Если вопросы не найдены, попробуем другой подход
        if not test_info['questions']:
            # Ищем все элементы, которые могут содержать вопросы
            question_elements = soup.find_all(['div', 'p', 'li'], text=re.compile(r'(?:Вопрос|^\d+[.)])', re.IGNORECASE))
            
            for elem in question_elements:
                text = elem.get_text().strip()
                if re.match(r'^(?:Вопрос\s*\d+|^\d+[.)])', text, re.IGNORECASE):
                    question = {
                        'number': len(test_info['questions']) + 1,
                        'text': text,
                        'options': [],
                        'correct_answer': ''
                    }
                    
                    # Ищем варианты ответов в следующих элементах
                    next_elem = elem.find_next_sibling()
                    while next_elem and not re.match(r'^(?:Вопрос|^\d+[.)])', next_elem.get_text(), re.IGNORECASE):
                        option_text = next_elem.get_text().strip()
                        if option_text and re.match(r'^[а-яa-z][.)]\s*', option_text, re.IGNORECASE):
                            question['options'].append(option_text)
                        next_elem = next_elem.find_next_sibling()
                    
                    if question['text'] or question['options']:
                        test_info['questions'].append(question)
        
        # Обновляем количество вопросов
        if test_info['questions']:
            test_info['questions_count'] = str(len(test_info['questions']))
        
        return test_info
        
    except Exception as e:
        print(f"Ошибка при парсинге страницы: {e}")
        import traceback
        traceback.print_exc()
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
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 20px;
            color: #333;
            border-bottom: 3px solid #007bff;
            padding-bottom: 15px;
        }}
        .test-info {{
            text-align: center;
            font-size: 0.9em;
            color: #666;
            margin-bottom: 40px;
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
        }}
        .test-info p {{
            margin: 8px 0;
        }}
        .test-info strong {{
            color: #333;
        }}
        .description {{
            margin-bottom: 40px;
            padding: 20px;
            background-color: #e9ecef;
            border-radius: 8px;
            border-left: 4px solid #007bff;
        }}
        .questions {{
            margin-top: 30px;
        }}
        .question {{
            margin-bottom: 30px;
            padding: 20px;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            background-color: #fff;
            transition: box-shadow 0.3s ease;
        }}
        .question:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .question-number {{
            font-weight: bold;
            font-size: 1.1em;
            color: #007bff;
            margin-bottom: 10px;
        }}
        .question-text {{
            margin-bottom: 15px;
            font-size: 1.05em;
            color: #333;
        }}
        .options {{
            margin-left: 20px;
            list-style-type: none;
            padding-left: 0;
        }}
        .options li {{
            margin: 8px 0;
            padding: 8px 12px;
            background-color: #f8f9fa;
            border-radius: 4px;
            border-left: 3px solid #dee2e6;
            transition: all 0.2s ease;
        }}
        .options li:hover {{
            background-color: #e9ecef;
            border-left-color: #007bff;
        }}
        .correct-answer {{
            margin-top: 15px;
            padding: 10px 15px;
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 4px;
            color: #155724;
            font-weight: bold;
        }}
        .no-questions {{
            text-align: center;
            padding: 40px;
            color: #666;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="container">
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
    if test_info.get('questions'):
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
                <div class="question-text">{q.get('text', '')}</div>
                <ul class="options">
                    {options_html}
                </ul>
                {correct_answer_html}
            </div>
            """
    else:
        questions_html = '<div class="no-questions">Вопросы не найдены. Возможно, требуется авторизация для просмотра полного содержимого теста.</div>'
    
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
    
    print("Парсинг страницы с улучшенным алгоритмом...")
    test_info = parse_studizba_test(url)
    
    if test_info:
        # Сохраняем результат в HTML файл
        html_content = format_test_html(test_info)
        with open('test_formatted_advanced.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Сохраняем также в JSON для отладки
        with open('test_data_advanced.json', 'w', encoding='utf-8') as f:
            json.dump(test_info, f, ensure_ascii=False, indent=2)
        
        print("Парсинг завершен!")
        print(f"HTML файл сохранен: test_formatted_advanced.html")
        print(f"JSON данные сохранены: test_data_advanced.json")
        print(f"Найдено вопросов: {len(test_info.get('questions', []))}")
    else:
        print("Не удалось распарсить страницу")