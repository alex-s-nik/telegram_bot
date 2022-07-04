import logging
import os
import sys
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


def send_message(bot, message):
    """Отправляет сообщение в Telegram."""
    bot.send_message(TELEGRAM_CHAT_ID, message)
    main.logger.info(f'Бот отправил сообщение {message}')


def get_api_answer(current_timestamp):
    """Возвращает ответ от API в формате json."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    error_message = 'Ошибка при доступе к API'

    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except Exception:
        raise Exception(error_message)

    if response.status_code != HTTPStatus.OK:
        raise Exception(error_message)

    return response.json()


def check_response(response):
    """Возвращает список домашних работ."""
    if not isinstance(response, dict):
        raise TypeError('Ответ от API не является словарем')

    if 'homeworks' not in response:
        raise Exception('Ключа "homeworks" нет в ответе от API')

    if not isinstance(response['homeworks'], list):
        raise Exception('Домашние работы из API не являются списком')

    return response['homeworks']


def parse_status(homework):
    """Возвращает сообщение со статусом домашней работы."""
    try:
        homework_name = homework['homework_name']
    except KeyError:
        raise KeyError('У домашней работы нет названия')

    try:
        homework_status = homework['status']
    except KeyError:
        raise KeyError('У домашней работы нет статуса')

    if homework_status not in HOMEWORK_STATUSES:
        raise Exception('Неверный статус у домашней работы')

    verdict = HOMEWORK_STATUSES[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность используемых переменных окружения."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(tokens)


def get_logger():
    """Возвращает логгер."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    log_handler = logging.StreamHandler(stream=sys.stdout)

    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    )
    log_handler.setFormatter(formatter)

    logger.addHandler(log_handler)

    return logger


def main():
    """Основная логика работы бота."""
    logger = get_logger()

    if not check_tokens():
        error_message = 'Не заданы одна или несколько переменных окружения'
        logger.critical(error_message)
        sys.exit(1)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    last_message = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)

            if homeworks:
                homework = homeworks[0]
            else:
                raise Exception('Список домашних работ пуст')

            message = parse_status(homework)
            if last_message != message:
                send_message(bot, message)

                last_message = message
            else:
                logger.debug('В ответе нет новых статусов')

        except telegram.error.TelegramError:
            logger.error('Сбой отправки сообщения в Telegram')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
