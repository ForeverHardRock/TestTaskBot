from classes import PaginationCallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
import os

load_dotenv()
channel_id = os.getenv('CHANNEL_ID')
channel_name = os.getenv('CHANNEL_NAME')


subs_key = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Подписаться", url=f"https://t.me/{channel_name}", callback_data="subscribe")
        ],
        [
            InlineKeyboardButton(text="Проверить подписку", callback_data="check_subscribe")
        ],
    ],
)

add_to_cart_key = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Добавить в корзину", callback_data="add_to_cart")
        ],
    ],
)


submit_key = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Добавить в корзину", callback_data="submit_to_cart")
        ],
    ],
)


pay_key = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Оплатить", callback_data="PAY")
        ],
    ],
)


menu_key = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Каталог"),
            KeyboardButton(text="Корзина")
        ],
        [
            KeyboardButton(text="FAQ")
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder='Выберите раздел: '
)

home_key = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="В начало")
        ],
    ],
    resize_keyboard=True,
)


def category_key(sub_btns):
    btns = []
    for btn in sub_btns:
        btns.append([InlineKeyboardButton(text=f"{btn}", callback_data=f"{btn}")])
    kb = InlineKeyboardMarkup(
        inline_keyboard=btns,
    )
    return kb


def delete_from_cart_key(pos):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Удалить из корзины", callback_data=str(pos))
            ],
        ],
    )
    return kb


to_order_key = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Оформить заказ", callback_data='TO_ORDER')
        ],
    ],
)


pagination_call = PaginationCallbackData("paginate")


class InlineKeyboardPaginator:
    def __init__(self, data, items_per_page):
        self.data = data
        self.items_per_page = items_per_page

    def get_keyboard(self, page):
        start_index = (page - 1) * self.items_per_page
        end_index = start_index + self.items_per_page
        btns = []
        for item in self.data[start_index:end_index]:
            btns.append([InlineKeyboardButton(text=item, callback_data=item)])
        if page > 1:
            btns.append([InlineKeyboardButton(text='Предыдущая', callback_data=pagination_call.new(action='prev', page=page))])
        if end_index < len(self.data):
            btns.append([InlineKeyboardButton(text='Следующая', callback_data=pagination_call.new(action='next', page=page))])
        kb = InlineKeyboardMarkup(row_width=1, inline_keyboard=btns)
        return kb