import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (
    APIAccessError,
    APIWrongStatusError,
    HomeworkEmptyError,
    ParseStatusError,
    ResponseError,
    TelegramSendingProblemError
)

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


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправляет сообщение в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        main.logger.info(f'Бот отправил сообщение {message}')
    except telegram.error.TelegramError as error:
        raise TelegramSendingProblemError(
            f'Сообщение "{message}" не было отправлено из-за ошибки {error}.'
        )


def get_api_answer(current_timestamp: int) -> dict:
    """Возвращает ответ от API в формате json."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except Exception as error:
        raise APIAccessError(
            f'Ошибка при доступе к API. '
            f'Ошибка: {error} '
            f'Путь: {ENDPOINT}, заголовки: {HEADERS}, параметры: {params}'
        )

    if response.status_code != HTTPStatus.OK:
        raise APIWrongStatusError(
            f'Неверный ответ от сервера. Status code: {response.status_code}. '
            f'Путь: {ENDPOINT}'
        )

    return response.json()


def check_response(response: dict) -> list:
    """Возвращает список домашних работ."""
    if not isinstance(response, dict):
        raise ResponseError('Ответ от API не является словарем')

    if 'homeworks' not in response:
        raise ResponseError('Ключа "homeworks" нет в ответе от API')

    if not isinstance(response['homeworks'], list):
        raise ResponseError('Домашние работы из API не являются списком')

    return response['homeworks']


def parse_status(homework: dict) -> str:
    """Возвращает сообщение со статусом домашней работы."""
    try:
        homework_name = homework['homework_name']
    except KeyError as error:
        raise ParseStatusError(
            'У домашней работы нет названия. '
            f'Ошибка: {error}'
        )

    try:
        homework_status = homework['status']
    except KeyError as error:
        raise ParseStatusError(
            'У домашней работы нет статуса. '
            f'Ошибка: {error}')

    if homework_status not in HOMEWORK_VERDICTS:
        raise ParseStatusError('Неверный статус у домашней работы')

    verdict = HOMEWORK_VERDICTS[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверяет доступность используемых переменных окружения."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(tokens)


def get_logger() -> logging.Logger:
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


def main() -> None:
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
                raise HomeworkEmptyError('Список домашних работ пуст')

            message = parse_status(homework)
            if last_message != message:
                send_message(bot, message)

                last_message = message
            else:
                logger.debug('В ответе нет новых статусов')

        except TelegramSendingProblemError:
            logger.error('Сбой отправки сообщения в Telegram')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
