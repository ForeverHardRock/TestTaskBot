import asyncio
import datetime
import logging
import sys
import os

from aiogram import Bot, Dispatcher
from aiogram import F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, URLInputFile, LabeledPrice, PreCheckoutQuery, InlineQuery, \
    InlineQueryResultArticle, InputTextMessageContent
from dotenv import load_dotenv
from keyboards import subs_key, menu_key, home_key, category_key, submit_key, add_to_cart_key, delete_from_cart_key, \
    to_order_key, pay_key, InlineKeyboardPaginator
from functions import get_from_db, get_product, save_to_cart, get_user_cart, delete_from_user_cart, order_to_db, \
    client_update, get_faq, check_mailing, load_all_users
from classes import PaginationCallbackData, Form
from aiogram.client.bot import DefaultBotProperties


load_dotenv()
TOKEN = os.getenv('API_KEY')
PAYMENTS_TOKEN = os.getenv('PAYMENTS_TOKEN')
channel_id = os.getenv('CHANNEL_ID')
channel_name = os.getenv('CHANNEL_NAME')
items_per_page = 5
dp = Dispatcher()
bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

pagination_call = PaginationCallbackData("paginate")


@dp.callback_query(lambda callback: pagination_call.prefix in callback.data)
async def callback_paginate(callback: CallbackQuery, state: FSMContext):
    data = pagination_call.parse(callback.data)
    action = data[1]
    page = int(data[2])
    items_all = await state.get_data()
    items = items_all['items']
    paginator = InlineKeyboardPaginator(items, items_per_page)
    await callback.answer()
    if action == 'next':
        page += 1
    elif action == 'prev' and page > 1:
        page -= 1
    await callback.message.edit_reply_markup(reply_markup=paginator.get_keyboard(page))


async def check_subscribe(user_id: int) -> bool:
    try:
        chat_member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Error checking subscription: {e}")
        return False


@dp.message(CommandStart())
async def start(message: Message) -> None:
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    is_subscribed = await check_subscribe(user_id)
    if is_subscribed:
        await message.answer(f"Привет, {message.from_user.full_name}! Приятного пользования!", reply_markup=menu_key)
        await client_update(user_id, user_name)
    else:
        await message.answer(f"Привет, {message.from_user.full_name}! Для пользования ботом нужно быть подписанным на канал!", reply_markup=subs_key)


@dp.callback_query(F.data == 'check_subscribe')
async def update_subs(callback: CallbackQuery):
    user_id = callback.from_user.id
    is_subscribed = await check_subscribe(user_id)
    if is_subscribed:
        await callback.message.answer(f"Приятного пользования!", reply_markup=menu_key)
    else:
        await callback.message.answer(f"Вы все еще не подписаны!", reply_markup=subs_key)


@dp.message(F.text == 'В начало')
async def cancel(message: Message, state: FSMContext) ->None:
    await state.clear()
    await message.answer('Меню:', reply_markup=menu_key)


@dp.message(F.text == 'Каталог')
async def catalog(message: Message, state: FSMContext) -> InlineKeyboardPaginator:
    categories = await get_from_db('category')
    await state.update_data(items=categories)
    paginator = InlineKeyboardPaginator(categories, items_per_page)
    await message.answer(f'Категории:', reply_markup=home_key)
    await message.answer(f'Выберите категорию', reply_markup=paginator.get_keyboard(1))
    await state.set_state(Form.catalog_category)
    return paginator


@dp.callback_query(Form.catalog_category)
async def catalog_categories(callback: CallbackQuery, state: FSMContext) -> None:
    subcategories = await get_from_db('subcategory', ['sub_category', callback.data])
    paginator = InlineKeyboardPaginator(subcategories, items_per_page)
    await callback.message.answer(f'Подкатегории:', reply_markup=home_key)
    await callback.message.answer(f'Выберите подкатегорию', reply_markup=paginator.get_keyboard(1))
    await state.update_data(items=subcategories)
    await state.update_data(catalog_category=callback.data)
    await state.set_state(Form.catalog_subcategory)


@dp.callback_query(Form.catalog_subcategory)
async def catalog_products(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    products = await get_from_db('product', ['prod_subcategory', callback.data])
    await state.update_data(items=products)
    paginator = InlineKeyboardPaginator(products, items_per_page)
    if len(products) > 0:
        await callback.message.answer(f'Товары:', reply_markup=home_key)
        await callback.message.answer(f'Выберите товар', reply_markup=paginator.get_keyboard(1))
        await state.set_state(Form.catalog_product)
    else:
        subcategories = await get_from_db('subcategory', ['sub_category', data['catalog_category']])
        await callback.message.answer(f'В подкатегории {callback.data} пока что нет товаров',  reply_markup=home_key)
        await callback.message.answer(f'Выберите другую подкатегорию', reply_markup=category_key(subcategories))


@dp.callback_query(Form.catalog_product)
async def catalog_product(callback: CallbackQuery, state: FSMContext) -> None:
    product = await get_product(callback.data)
    await bot.send_photo(
        chat_id=callback.from_user.id,
        photo=URLInputFile(product['prod_image']),
        caption=f"{product['prod_name']}\n"
                f"Цена: {product['prod_price']}\n\n"
                f"{product['prod_desc']}",
        reply_markup=add_to_cart_key
    )
    await state.update_data(catalog_product=product)
    await state.set_state(Form.catalog_quantity)


@dp.callback_query(Form.catalog_quantity)
async def catalog_quantity(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    product = data['catalog_product']
    await callback.message.answer(f"{product['prod_name']}\n"
                                  f"Цена: {product['prod_price']}\n\n",
                                  reply_markup=home_key
                                  )
    await callback.message.answer(f"Введите необходимое количество данного товара")
    await state.set_state(Form.catalog_confirm)


@dp.message(F.text, Form.catalog_confirm)
async def catalog_confirm(message: Message, state: FSMContext) -> None:
    quantity = message.text
    try:
        quantity = int(quantity)
        if quantity > 0:
            data = await state.get_data()
            product = data['catalog_product']
            price = float(product['prod_price'])
            total_price = price * quantity
            await message.answer(f"{product['prod_name']}. Количество: {quantity}шт.\n"
                                 f"Итоговая цена: {total_price}\n\n",
                                 reply_markup=home_key
                                 )
            await message.answer(f"Подтвердите выбор:", reply_markup=submit_key)
            await state.update_data(catalog_quantity=quantity)
            await state.update_data(catalog_total=total_price)
            await state.set_state(Form.catalog_to_base)
        else:
            await message.answer('Количество должно быть положительным!', reply_markup=home_key)
    except Exception as e:
        print(e)
        await message.answer('Введите целое число', reply_markup=home_key)


@dp.callback_query(Form.catalog_to_base)
async def catalog_save_to_base(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    product = data['catalog_product']
    user_id = callback.from_user.id
    finish_data = [
        product['prod_name'],
        float(product['prod_price']),
        int(data['catalog_quantity']),
        float(data['catalog_total'])
    ]
    await save_to_cart(user_id, finish_data)
    await callback.message.answer('Корзина сохранена!', reply_markup=menu_key)
    await state.clear()


@dp.message(F.text == 'Корзина')
async def add_to_cart(message: Message, state: FSMContext) -> None:
    data = await get_user_cart(message.from_user.id)
    if data:
        data = eval(data[0])
        await message.answer('Ваша корзина:', reply_markup=home_key)
        total_score = 0
        total_price = 0
        mes_list = {}
        for pos in data:
            total_score += int(pos[2])
            total_price += float(pos[3])
            msg = await message.answer(f"Товар: {pos[0]}, цена:{pos[1]}"
                                 f"Кол-во: {pos[2]}, итого:{pos[3]}",
                                 reply_markup=delete_from_cart_key(pos)
                                 )
            mes_list.update({str(pos):msg.message_id})
        await state.update_data(mes_ids=mes_list)
        total_msg = await message.answer(f'Итого: {total_score} товаров на сумму {total_price}', reply_markup=to_order_key)
        await state.update_data(total_id=total_msg.message_id)
        await state.update_data()
        await state.set_state(Form.to_cart_view)
    else:
        await message.answer('Ваша корзина пуста', reply_markup=menu_key)


@dp.callback_query(Form.to_cart_view)
async def to_order(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data == 'TO_ORDER':
        await callback.message.answer('Введите данные для доставки:')
        await state.set_state(Form.to_cart_address)

    else:
        data = await state.get_data()
        msg_list = data['mes_ids']
        total_msg_id = data['total_id']

        pos = callback.data
        mes_id = msg_list[pos]

        msg_list.pop(pos)
        await state.update_data(mes_ids=msg_list)
        keys_list = list(msg_list.keys())
        new_score = 0
        new_price = 0
        for key in keys_list:
            pos_list = eval(key)
            new_score += int(pos_list[2])
            new_price += float(pos_list[3])

        await bot.delete_message(chat_id=callback.from_user.id, message_id=mes_id)
        await bot.delete_message(chat_id=callback.from_user.id, message_id=total_msg_id)
        await delete_from_user_cart(callback.from_user.id, callback.data)
        if new_score > 0:
            total_msg = await callback.message.answer(f'Итого: {new_score} товаров на сумму {new_price}', reply_markup=to_order_key)
            await state.update_data(total_id=total_msg.message_id)
        else:
            await callback.message.answer('Ваша корзина пуста', reply_markup=menu_key)
            await state.clear()


@dp.message(F.text, Form.to_cart_address)
async def get_address(message: Message, state: FSMContext) -> None:
    address = message.text
    if address != '':
        data = await state.get_data()
        msg_list = data['mes_ids']
        positions = list(msg_list.keys())
        new_score = 0
        new_price = 0
        products = ''
        for position in positions:
            pos_list = eval(position)
            products = products + f'\n• {pos_list[0]} {pos_list[2]}шт. - {pos_list[3]}'
            new_score += int(pos_list[2])
            new_price += float(pos_list[3])
        await state.update_data(mes_ids=positions)
        await state.update_data(address=address)
        await message.answer(f"Итого {new_score} товаров:"
                             f"{products}"
                             f"\nОбщая сумма - {new_price}"
                             f"\nАдрес доставки: {address}",
                             reply_markup=pay_key
                             )
        await state.update_data(price=new_price)
        # await state.set_state(Form.pay1)
        await state.set_state(Form.pay4)
    else:
        await message.answer('Введите адрес')


@dp.callback_query(Form.pay1)
async def oform_pay(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pay_summ = int(data['price'] * 100)

    PRICE = LabeledPrice(label='Пополнение счета', amount=pay_summ)
    if PAYMENTS_TOKEN.split(':')[1] == 'TEST':
        await bot.send_message(callback.from_user.id, "Тестовый платеж!!!")
    await bot.send_invoice(callback.from_user.id,
                           title="Покупка товаров",
                           description="Оформление платежа",
                           provider_token=PAYMENTS_TOKEN,
                           currency="rub",
                           is_flexible=False,
                           prices=[PRICE],
                           start_parameter="one-month-subscription",
                           payload="test-invoice-payload")
    await state.set_state(Form.pay2)


@dp.pre_checkout_query(lambda query: True, Form.pay2)
async def pre_checkout_query(pre_checkout_q: PreCheckoutQuery, state: FSMContext):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)
    await state.set_state(Form.pay3)


@dp.message(Form.pay3)
async def successful_payment(message: Message, state: FSMContext):
    await message.answer(f"Платеж на сумму {message.successful_payment.total_amount // 100} {message.successful_payment.currency} прошел успешно!", reply_markup=menu_key)

    data = await state.get_data()
    await order_to_db(data['mes_ids'], data['address'], data['price'], message.from_user.first_name, message.from_user.id)
    await state.clear()
    print("SUCCESSFUL PAYMENT:")


# Обход платежки
@dp.callback_query(Form.pay4)
async def check(callback: CallbackQuery, state:FSMContext):
    data = await state.get_data()
    await order_to_db(data['mes_ids'], data['address'], data['price'], callback.from_user.first_name, callback.from_user.id)
    await callback.message.answer('Заказ оплачен!', reply_markup=menu_key)
    await state.clear()


@dp.message(F.text == 'FAQ')
async def faq_handler(message: Message, state: FSMContext):
    await message.answer('Введите ваш вопрос', reply_markup=home_key)
    await state.update_data(inline=True)


@dp.inline_query()
async def on_inline_query(inline_query: InlineQuery, state: FSMContext):
    data = await state.get_data()
    try:
        inline_mode = data['inline']
    except:
        inline_mode = None
    if inline_mode:
        faq = await get_faq()
        query = inline_query.query.lower()
        results = []
        for question, answer in faq.items():
            if query in question.lower():
                results.append(
                    InlineQueryResultArticle(
                        id=question,
                        title=question,
                        input_message_content=InputTextMessageContent(message_text=answer),
                    )
                )
        await bot.answer_inline_query(inline_query.id, results=results)


async def mailing() -> None:
    time_now = datetime.datetime.now().replace(microsecond=0)
    await asyncio.sleep(30)
    await send_mails(time_now)


async def send_mails(time_now):
    mails = await check_mailing(time_now)
    if mails:
        users_ids = await load_all_users()
        if users_ids:
            for mail in mails:
                for user_id in users_ids:
                    await bot.send_message(int(user_id[0]), mail[0])


async def main() -> None:
    await asyncio.gather(
        dp.start_polling(bot),
        mailing()
    )


if __name__ == "__main__":
    # logging.basicConfig(level=logging.INFO, filename='bot.log')
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())

