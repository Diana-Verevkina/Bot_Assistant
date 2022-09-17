PRACTICUM_TOKEN = None
TELEGRAM_TOKEN = 6789
TELEGRAM_CHAT_ID = 987


tokens = (
    ['PRACTICUM_TOKEN', PRACTICUM_TOKEN],
    ['TELEGRAM_TOKEN', TELEGRAM_TOKEN],
    ['TELEGRAM_CHAT_ID', TELEGRAM_CHAT_ID]
)
for token in tokens:
    if not token[1]:
        print(f'Ошибка {token[0]}')

