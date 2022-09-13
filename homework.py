import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s, %(name)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)
old_message = ''


def send_message(bot, message):
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Сообщение успешно отправлено')
    except:
        logging.error('Сбой в отправке сообщения')


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    # params = {'from_date': 0}
    try:
        homework_statuses = requests.get(ENDPOINT, headers=HEADERS,
                                         params=params)
    except:
        logging.error('Эндпоинт не доступен')
    else:
        if homework_statuses.status_code == HTTPStatus.OK:
            logging.info('Успешное получение эндпоинта')
            return homework_statuses.json()
        elif homework_statuses.status_code == HTTPStatus.INTERNAL_SERVER_ERROR:
            logging.error('Ошибка доступа INTERNAL_SERVER_ERROR')
            raise SystemError('Ошибка доступа INTERNAL_SERVER_ERROR')
        elif homework_statuses.status_code == HTTPStatus.REQUEST_TIMEOUT:
            logging.error('Ошибка доступа REQUEST_TIMEOUT')
            raise SystemError('Ошибка доступа REQUEST_TIMEOUT')
        else:
            logging.error(f'Ошибка доступа {homework_statuses.status_code}')
            raise SystemError(
                f'Ошибка доступа {homework_statuses.status_code}'
            )


def check_response(response):
    if type(response) == dict:
        if response['current_date']:
            try:
                homeworks = response['homeworks']
            except:
                logging.error('Отсутствие ключа homeworks в запросе')
            if type(homeworks) == list:
                return homeworks
            else:
                raise TypeError('homeworks вернул не список')
    else:
        raise TypeError('homework вернул не словарь')


def parse_status(homework):
    homework_name = homework['homework_name']
    homework_status = homework['status']

    if homework_status and homework_name:
        if homework_status in HOMEWORK_STATUSES:
            verdict = HOMEWORK_STATUSES[homework_status]
            return (f'Изменился статус проверки работы '
                    f'"{homework_name}". {verdict}')
        else:
            logging.error('Полученный статус отсутствует в списке '
                          'HOMEWORK_STATUSES')
            raise KeyError('Полученный статус отсутствует в списке '
                           'HOMEWORK_STATUSES')
    else:
        logging.error('Ключ homework_name/homework_status отсутствует '
                      'в словаре')
        raise KeyError('Ключ homework_name/homework_status отсутствует '
                       'в словаре')


def check_tokens():
    if not PRACTICUM_TOKEN:
        logging.critical('Ошибка PRACTICUM_TOKEN')
        return False
    elif not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logging.critical('Ошибка TELEGRAM_TOKEN или TELEGRAM_CHAT_I')
        return False
    else:
        return True


def main():
    """Основная логика работы бота."""
    global old_message
    # payload = {'from_date': 1549962000}
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if not check_tokens():
        raise SystemExit('Выход из системы')

    while True:
        try:
            response = get_api_answer(current_timestamp)
            response = check_response(response)

            if len(response) > 0:
                homework_status = parse_status(response[0])
                if homework_status:
                    send_message(bot, homework_status)
                else:
                    logging.debug('Новые статусы отсутствуют')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            try:
                if message != old_message:
                    bot.send_message(TELEGRAM_CHAT_ID, message)
                    logging.info('Сообщение о сбое успешно отправлено')
            except:
                logging.error('Сбой в отправке сообщения о сбое в программе')
        finally:
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
