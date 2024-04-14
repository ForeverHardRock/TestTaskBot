from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from keyboards import subs_key, menu_key
from functions import client_update, check_subscribe

router = Router(name=__name__)


@router.message(CommandStart())
async def start(message: Message) -> None:
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    is_subscribed = await check_subscribe(user_id)
    if is_subscribed:
        await message.answer(f"Привет, {message.from_user.full_name}! Приятного пользования!", reply_markup=menu_key)
        await client_update(user_id, user_name)
    else:
        await message.answer(f"Привет, {message.from_user.full_name}! Для пользования ботом нужно быть подписанным на канал!", reply_markup=subs_key)


@router.callback_query(F.data == 'check_subscribe')
async def update_subs(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    is_subscribed = await check_subscribe(user_id)
    if is_subscribed:
        await callback.message.answer(f"Приятного пользования!", reply_markup=menu_key)
    else:
        await callback.message.answer(f"Вы все еще не подписаны!", reply_markup=subs_key)


@router.message(F.text == 'В начало')
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer('Меню:', reply_markup=menu_key)

