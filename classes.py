from aiogram.fsm.state import StatesGroup, State


class PaginationCallbackData:
    def __init__(self, prefix):
        self.prefix = prefix

    def new(self, action: str, page: int):
        return f"{self.prefix}:{action}:{page}"

    def parse(self, data: str):
        return data.split(':')


class Form(StatesGroup):
    catalog_category = State()
    catalog_subcategory = State()
    catalog_product = State()
    catalog_quantity = State()
    catalog_confirm = State()
    catalog_to_base = State()
    to_cart_view = State()
    to_cart_address = State()
    pay1 = State()
    pay2 = State()
    pay3 = State()
    pay4 = State()
    faq_ready = State()
