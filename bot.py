import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

import database as db
from config import BOT_TOKEN
from handlers import *

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


def main():
    db.init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # ─── Menu Utama Callback ────────────────────────
    app.add_handler(CallbackQueryHandler(menu_main, pattern=r"^menu_main$"))

    # ─── Command handlers ───────────────────────────
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))

    # ─── Menu navigasi callbacks ────────────────────
    app.add_handler(CallbackQueryHandler(help_cmd, pattern=r"^menu_help$"))

    # ─── Add transaction conversation ───────────────
    add_conv = ConversationHandler(
        entry_points=[CommandHandler("add", add_start), CallbackQueryHandler(add_start, pattern=r"^menu_add$")],
        states={
            ADD_CHOICE: [CallbackQueryHandler(add_choice_callback, pattern=r"^add_")],
            ADD_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_amount)],
            ADD_CATEGORY: [CallbackQueryHandler(add_category_callback, pattern=r"^addcat_")],
            ADD_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_note)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CallbackQueryHandler(menu_main, pattern=r"^menu_main$")],
        allow_reentry=True,
    )
    app.add_handler(add_conv)

    # ─── Laporan ───────────────────────────────────
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CallbackQueryHandler(report_callback, pattern=r"^report_\d+_\d+$"))
    app.add_handler(CallbackQueryHandler(report, pattern=r"^menu_report$"))

    # ─── Budget conversation ───────────────────────
    budget_conv = ConversationHandler(
        entry_points=[CommandHandler("budget", budget), CallbackQueryHandler(budget, pattern=r"^menu_budget$")],
        states={
            BUDGET_AMOUNT: [
                CallbackQueryHandler(budget_category_callback, pattern=r"^bgtcat_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, budget_amount),
            ],
            BUDGET_DELETE: [CallbackQueryHandler(budget_delete_callback, pattern=r"^bgt_del_")],
        },
        fallbacks=[CommandHandler("cancel", cancel), CallbackQueryHandler(menu_main, pattern=r"^menu_main$")],
        allow_reentry=True,
    )
    app.add_handler(budget_conv)
    app.add_handler(CallbackQueryHandler(budget_callback, pattern=r"^budget_"))

    # ─── Categories conversation ───────────────────
    cat_conv = ConversationHandler(
        entry_points=[CommandHandler("categories", categories), CallbackQueryHandler(categories, pattern=r"^menu_categories$")],
        states={
            CAT_ADD_NAME: [
                CallbackQueryHandler(cat_add_type_callback, pattern=r"^catadd_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, cat_add_name),
            ],
            CAT_DELETE: [CallbackQueryHandler(cat_delete_callback, pattern=r"^catdel_")],
        },
        fallbacks=[CommandHandler("cancel", cancel), CallbackQueryHandler(menu_main, pattern=r"^menu_main$")],
        allow_reentry=True,
    )
    app.add_handler(cat_conv)
    app.add_handler(CallbackQueryHandler(categories_callback, pattern=r"^cat_"))

    app.run_polling()


if __name__ == "__main__":
    main()
