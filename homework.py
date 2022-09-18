import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
import telegram.error
from dotenv import load_dotenv

from exceptions import EmptyAnswerFromAPI, InvalidResponseCode

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(BASE_DIR, 'main.log')

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(lineno)d, %(asctime)s, %(levelname)s, %(message)s, %(name)s')

handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

handler_file = logging.FileHandler(DIR, encoding='UTF-8')
logger.addHandler(handler_file)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        logging.info('Начало отправки сообщения со статусом '
                     'домашней работы в telegram')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as error:
        logging.error(f'Сбой в отправке сообщения {error}')
    else:
        logging.info('Успешная отправка сообщения со статусом '
                     'домашней работы в telegram')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp
    # params = {'from_date': timestamp}
    # params = {'from_date': 0}
    get_api_dict = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }
    logging.info(
        "Начали запрос к API endpoint: {url}, headers: {headers}, "
        "params: {params}".format(**get_api_dict))

    try:
        """homework_statuses = requests.get(
            get_api_dict['url'], headers=get_api_dict['headers'],
            params=get_api_dict['params']
        )"""
        homework_statuses = requests.get(**get_api_dict)
        if homework_statuses.status_code != HTTPStatus.OK:
            msg = (
                f'http status: {homework_statuses.status_code} '
                f'reason: {homework_statuses.reason} '
                f'text: {homework_statuses.text}'
            )
            raise InvalidResponseCode(msg)
        return homework_statuses.json()
    except Exception as error:
        raise ConnectionError(
            "error: {}, endpoint: {url}, headers: {headers}, "
            "params: {params}".format(error, **get_api_dict)
        )


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('homework вернул не словарь')
    if 'homeworks' not in response:
        raise EmptyAnswerFromAPI('Отсутствие ключа homeworks в запросе')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise KeyError('homeworks вернул не список')
    return homeworks


def parse_status(homework):
    """Извлекает статус домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует значение homework_name')
    if 'status' not in homework:
        raise KeyError('Отсутствует значение status')
    if homework.get('status') not in HOMEWORK_VERDICTS:
        raise ValueError('Получен неизвестный статус')

    return (
        'Изменился статус проверки работы "{homework_name}". '
        '{verdict}'.format(homework_name=homework.get('homework_name'),
                           verdict=HOMEWORK_VERDICTS[homework.get('status')]))


def check_tokens():
    """Проверяет доступность переменных окружения."""
    check_token = True
    tokens = (
        ['PRACTICUM_TOKEN', PRACTICUM_TOKEN],
        ['TELEGRAM_TOKEN', TELEGRAM_TOKEN],
        ['TELEGRAM_CHAT_ID', TELEGRAM_CHAT_ID],
    )

    for token_name, token in tokens:
        if not token:
            logging.info(f'Ошибка {token_name}')
            check_token = False
    return check_token


def main():
    """Основная логика работы бота."""
    current_timestamp = int(time.time())
    if not check_tokens():
        raise SystemExit('Выход из системы')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_report = {
        'name': None,
        'message': None
    }
    prev_report = current_report.copy()

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                homework_status = parse_status(homework)
                current_report['name'] = homework.get('homework_name')
                current_report['message'] = homework.get(
                    'reviewer_comment'
                )
            else:
                logging.info('Пустой ответ от API')
            if current_report != prev_report:
                send_message(bot, homework_status)
                current_timestamp = response.get('current_date',
                                                 int(time.time()))
                prev_report = current_report.copy()
            else:
                logging.debug('Новые статусы отсутствуют')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            current_report['message'] = message
            if current_report != prev_report:
                send_message(bot, message)
                logger.error(message)
                prev_report = current_report.copy()
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
