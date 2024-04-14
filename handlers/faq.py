from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message,  InlineQuery,InlineQueryResultArticle, InputTextMessageContent
from keyboards import home_key
from functions import get_faq
from bot import bot

router = Router(name=__name__)


@router.message(F.text == 'FAQ')
async def faq_handler(message: Message, state: FSMContext):
    await message.answer('Введите ваш вопрос', reply_markup=home_key)
    await state.update_data(inline=True)


@router.inline_query()
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

