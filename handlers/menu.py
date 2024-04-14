from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, URLInputFile
from keyboards import menu_key, home_key, category_key, submit_key, add_to_cart_key, InlineKeyboardPaginator
from functions import get_from_db, get_product, save_to_cart
from classes import Form, PaginationCallbackData
from bot import bot

router = Router(name=__name__)
pagination_call = PaginationCallbackData("paginate")
items_per_page = 5


@router.callback_query(lambda callback: pagination_call.prefix in callback.data)
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


@router.message(F.text == 'Каталог')
async def catalog(message: Message, state: FSMContext) -> InlineKeyboardPaginator:
    categories = await get_from_db('category')
    await state.update_data(items=categories)
    paginator = InlineKeyboardPaginator(categories, items_per_page)
    await message.answer(f'Категории:', reply_markup=home_key)
    await message.answer(f'Выберите категорию', reply_markup=paginator.get_keyboard(1))
    await state.set_state(Form.catalog_category)
    return paginator


@router.callback_query(Form.catalog_category)
async def catalog_categories(callback: CallbackQuery, state: FSMContext) -> None:
    subcategories = await get_from_db('subcategory', ['sub_category', callback.data])
    paginator = InlineKeyboardPaginator(subcategories, items_per_page)
    await callback.message.answer(f'Подкатегории:', reply_markup=home_key)
    await callback.message.answer(f'Выберите подкатегорию', reply_markup=paginator.get_keyboard(1))
    await state.update_data(items=subcategories)
    await state.update_data(catalog_category=callback.data)
    await state.set_state(Form.catalog_subcategory)


@router.callback_query(Form.catalog_subcategory)
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


@router.callback_query(Form.catalog_product)
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


@router.callback_query(Form.catalog_quantity)
async def catalog_quantity(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    product = data['catalog_product']
    await callback.message.answer(f"{product['prod_name']}\n"
                                  f"Цена: {product['prod_price']}\n\n",
                                  reply_markup=home_key
                                  )
    await callback.message.answer(f"Введите необходимое количество данного товара")
    await state.set_state(Form.catalog_confirm)


@router.message(F.text, Form.catalog_confirm)
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


@router.callback_query(Form.catalog_to_base)
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
