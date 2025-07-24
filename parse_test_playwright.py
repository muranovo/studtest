#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
import json
import re

async def parse_with_playwright(url):
    """Парсит страницу с тестом используя playwright"""
    
    async with async_playwright() as p:
        # Запускаем браузер
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Переходим на страницу
            print(f"Загружаю страницу: {url}")
            await page.goto(url, wait_until='networkidle', timeout=60000)
            
            # Ждем загрузки контента
            await page.wait_for_timeout(3000)
            
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
            
            # Извлекаем заголовок
            title = await page.query_selector('h1')
            if title:
                test_info['title'] = await title.text_content()
                test_info['title'] = test_info['title'].strip()
            
            # Получаем весь текст страницы
            content = await page.content()
            text_content = await page.evaluate('() => document.body.innerText')
            
            # Ищем информацию о просмотрах и покупках
            views_match = re.search(r'(\d+)\s*просмотр', text_content)
            if views_match:
                test_info['views'] = views_match.group(1)
            
            purchases_match = re.search(r'(\d+)\s*(?:покуп|продаж)', text_content)
            if purchases_match:
                test_info['purchases'] = purchases_match.group(1)
            
            # Ищем информацию о пользователе
            user_match = re.search(r'(?:загруз|добав|пользователь|автор).*?([A-Za-z0-9_]+)', text_content, re.IGNORECASE)
            if user_match:
                test_info['uploaded_by'] = user_match.group(1)
            
            # Ищем информацию о результатах
            result_match = re.search(r'(?:сдан|результат).*?(\d+[,.]?\d*)\s*из\s*(\d+[,.]?\d*).*?(\d+%?)', text_content, re.IGNORECASE)
            if result_match:
                test_info['last_result'] = f"Последний раз тест был сдан на результат {result_match.group(1)} из {result_match.group(2)} ({result_match.group(3)}). Год сдачи — 2024-2025."
            
            # Парсим вопросы
            # Сначала попробуем найти вопросы через селекторы
            question_elements = await page.query_selector_all('[class*="question"], [class*="test-item"], [class*="quiz"]')
            
            if question_elements:
                for i, elem in enumerate(question_elements):
                    question_text = await elem.text_content()
                    question = {
                        'number': i + 1,
                        'text': question_text.strip(),
                        'options': [],
                        'correct_answer': ''
                    }
                    
                    # Ищем варианты ответов
                    options = await elem.query_selector_all('[class*="option"], [class*="answer"], li')
                    for opt in options:
                        opt_text = await opt.text_content()
                        if opt_text.strip():
                            question['options'].append(opt_text.strip())
                    
                    test_info['questions'].append(question)
            
            # Если вопросы не найдены через селекторы, парсим текст
            if not test_info['questions']:
                lines = text_content.split('\n')
                current_question = None
                question_number = 0
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Проверяем начало вопроса
                    question_match = re.match(r'^(?:Вопрос\s*(\d+)|(\d+)[.)])', line, re.IGNORECASE)
                    if question_match:
                        if current_question and (current_question['text'] or current_question['options']):
                            test_info['questions'].append(current_question)
                        
                        question_number += 1
                        current_question = {
                            'number': question_number,
                            'text': re.sub(r'^(?:Вопрос\s*\d+|^\d+[.)])\s*', '', line).strip(),
                            'options': [],
                            'correct_answer': ''
                        }
                    elif current_question:
                        # Проверяем варианты ответов
                        option_match = re.match(r'^([а-яa-z])[.)]\s*(.+)', line, re.IGNORECASE)
                        if option_match:
                            current_question['options'].append(line)
                        elif re.search(r'(?:правильн|верн|ответ)', line, re.IGNORECASE):
                            current_question['correct_answer'] = line
                        elif not current_question['options'] and len(line) > 10:
                            # Продолжение текста вопроса
                            current_question['text'] += ' ' + line
                
                if current_question and (current_question['text'] or current_question['options']):
                    test_info['questions'].append(current_question)
            
            # Обновляем количество вопросов
            if test_info['questions']:
                test_info['questions_count'] = str(len(test_info['questions']))
            
            # Делаем скриншот для отладки
            await page.screenshot(path='page_screenshot.png')
            
            return test_info
            
        except Exception as e:
            print(f"Ошибка при парсинге: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            await browser.close()

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
        .note {{
            margin-top: 40px;
            padding: 20px;
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            color: #856404;
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
        
        <div class="note">
            <p><strong>Примечание:</strong> Данная страница была создана автоматически на основе информации, доступной на сайте studizba.com. Для просмотра полного содержимого теста с ответами может потребоваться покупка или авторизация на исходном сайте.</p>
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

async def main():
    url = "https://studizba.com/files/grazhdanskoe-pravo/answers/371660-grazhdanskoe-pravo-temy-1-12.html"
    
    print("Парсинг страницы с использованием Playwright...")
    test_info = await parse_with_playwright(url)
    
    if test_info:
        # Сохраняем результат в HTML файл
        html_content = format_test_html(test_info)
        with open('test_formatted_playwright.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Сохраняем также в JSON для отладки
        with open('test_data_playwright.json', 'w', encoding='utf-8') as f:
            json.dump(test_info, f, ensure_ascii=False, indent=2)
        
        print("Парсинг завершен!")
        print(f"HTML файл сохранен: test_formatted_playwright.html")
        print(f"JSON данные сохранены: test_data_playwright.json")
        print(f"Скриншот страницы сохранен: page_screenshot.png")
        print(f"Найдено вопросов: {len(test_info.get('questions', []))}")
    else:
        print("Не удалось распарсить страницу")

if __name__ == "__main__":
    asyncio.run(main())