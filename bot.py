import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
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
from absensi_handlers import *

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

PORT = int(os.getenv("PORT", 8080))


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        logger.info("Health check: %s", format % args)


def run_http_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    logger.info("Health server running on port %d", PORT)
    server.serve_forever()


def main():
    db.init_db()

    t = threading.Thread(target=run_http_server, daemon=True)
    t.start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # ─── Menu Utama Callback ────────────────────────
    app.add_handler(CallbackQueryHandler(menu_main, pattern=r"^menu_main$"))
    app.add_handler(CallbackQueryHandler(menu_finance, pattern=r"^menu_finance$"))
    app.add_handler(CallbackQueryHandler(absensi_menu, pattern=r"^menu_absensi$"))

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

    # ─── ABSENSI ─────────────────────────────────────
    # Check-in flow (uses user_data, not ConversationHandler)
    app.add_handler(CallbackQueryHandler(abs_checkin, pattern=r"^abs_checkin$"))
    app.add_handler(CallbackQueryHandler(abs_pick_member, pattern=r"^abspick_"))
    app.add_handler(CallbackQueryHandler(abs_toggle_mode, pattern=r"^abs_toggle_mode$"))
    app.add_handler(CallbackQueryHandler(abs_save_checkin, pattern=r"^abs_save_checkin$"))

    # Custom date conversation
    abs_date_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(abs_custom_date, pattern=r"^abs_custom_date$")],
        states={
            ABSENSI_CUSTOM_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, abs_custom_date_text)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CallbackQueryHandler(menu_main, pattern=r"^menu_main$")],
        allow_reentry=True,
    )
    app.add_handler(abs_date_conv)

    # Anggota
    app.add_handler(CallbackQueryHandler(abs_list_members, pattern=r"^abs_list_members$"))
    app.add_handler(CallbackQueryHandler(abs_delete_member_start, pattern=r"^abs_delete_member$"))
    app.add_handler(CallbackQueryHandler(abs_delete_member_confirm, pattern=r"^absdel_"))

    abs_add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(abs_add_member_start, pattern=r"^abs_add_member$")],
        states={
            ABSENSI_ADD_MEMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, abs_add_member_text)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CallbackQueryHandler(menu_main, pattern=r"^menu_main$")],
        allow_reentry=True,
    )
    app.add_handler(abs_add_conv)

    # Cek absensi
    app.add_handler(CallbackQueryHandler(abs_check_today, pattern=r"^abs_check_today$"))

    abs_cek_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(abs_check_date_start, pattern=r"^abs_check_date$")],
        states={
            ABSENSI_CEK_TANGGAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, abs_check_date_text)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CallbackQueryHandler(menu_main, pattern=r"^menu_main$")],
        allow_reentry=True,
    )
    app.add_handler(abs_cek_conv)

    # Persentase
    abs_persen_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(abs_percentage_start, pattern=r"^abs_percentage$")],
        states={
            ABSENSI_PERSENTASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, abs_percentage_text)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CallbackQueryHandler(menu_main, pattern=r"^menu_main$")],
        allow_reentry=True,
    )
    app.add_handler(abs_persen_conv)

    # Hapus absen
    app.add_handler(CallbackQueryHandler(abs_delete_record_start, pattern=r"^abs_delete_record$"))
    app.add_handler(CallbackQueryHandler(abs_delete_record_confirm, pattern=r"^absdelrec_"))

    # Excel
    abs_excel_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(abs_excel_month, pattern=r"^abs_excel_month$")],
        states={
            ABSENSI_EXCEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, abs_excel_text)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CallbackQueryHandler(menu_main, pattern=r"^menu_main$")],
        allow_reentry=True,
    )
    app.add_handler(abs_excel_conv)

    logger.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
