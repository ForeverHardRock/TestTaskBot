from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from keyboards import menu_key, home_key, delete_from_cart_key, to_order_key, pay_key
from functions import get_user_cart, delete_from_user_cart
from classes import Form
from bot import bot

router = Router(name=__name__)


@router.message(F.text == 'Корзина')
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


@router.callback_query(Form.to_cart_view)
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


@router.message(F.text, Form.to_cart_address)
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