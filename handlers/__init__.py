__all__ = ('router',)

from .base import router as base_router
from .menu import router as menu_router
from .add_to_cart import router as cart_router
from .pay import router as pay_router
from .faq import router as faq_router
from aiogram import Router


router = Router()

router.include_routers(base_router, menu_router, cart_router, pay_router, faq_router)
