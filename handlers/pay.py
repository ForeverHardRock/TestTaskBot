import os
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from keyboards import menu_key
from functions import order_to_db
from classes import Form
from bot import bot
from aiogram import Router
from dotenv import load_dotenv

load_dotenv()
router = Router(name=__name__)
PAYMENTS_TOKEN = os.getenv('PAYMENTS_TOKEN')


@router.callback_query(Form.pay1)
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


@router.pre_checkout_query(lambda query: True, Form.pay2)
async def pre_checkout_query(pre_checkout_q: PreCheckoutQuery, state: FSMContext):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)
    await state.set_state(Form.pay3)


@router.message(Form.pay3)
async def successful_payment(message: Message, state: FSMContext):
    await message.answer(f"Платеж на сумму {message.successful_payment.total_amount // 100} {message.successful_payment.currency} прошел успешно!", reply_markup=menu_key)

    data = await state.get_data()
    await order_to_db(data['mes_ids'], data['address'], data['price'], message.from_user.first_name, message.from_user.id)
    await state.clear()
    print("SUCCESSFUL PAYMENT:")


# Обход платежки
@router.callback_query(Form.pay4)
async def check(callback: CallbackQuery, state:FSMContext):
    data = await state.get_data()
    await order_to_db(data['mes_ids'], data['address'], data['price'], callback.from_user.first_name, callback.from_user.id)
    await callback.message.answer('Заказ оплачен!', reply_markup=menu_key)
    await state.clear()

