from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

import database as db

(
    ADD_CHOICE,
    ADD_AMOUNT,
    ADD_CATEGORY,
    ADD_NOTE,
    BUDGET_AMOUNT,
    BUDGET_DELETE,
    CAT_ADD_NAME,
    CAT_DELETE,
) = range(8)

MONTH_NAMES = [
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]

# ─── Helper ────────────────────────────────────────────────

def menu_button():
    return [InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_main")]

def global_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Manajemen Keuangan", callback_data="menu_finance")],
        [InlineKeyboardButton("📋 Absensi", callback_data="menu_absensi")],
        [InlineKeyboardButton("❓ Bantuan", callback_data="menu_help")],
    ])

def finance_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Catat Transaksi", callback_data="menu_add")],
        [InlineKeyboardButton("📊 Laporan Keuangan", callback_data="menu_report")],
        [InlineKeyboardButton("🎯 Anggaran Budget", callback_data="menu_budget")],
        [InlineKeyboardButton("📁 Kelola Kategori", callback_data="menu_categories")],
    ] + [menu_button()])

def wrap_keyboard(buttons):
    return InlineKeyboardMarkup(buttons + [menu_button()])

def fmt_rp(amount):
    return f"Rp{amount:,.0f}"

# ─── Menu Utama ────────────────────────────────────────────

async def menu_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "🏠 *Menu Utama*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Pilih menu di bawah:"
    )
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=global_menu_keyboard())

async def menu_finance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if not db.default_categories_exist(user_id):
        db.seed_default_categories(user_id)

    now = datetime.now()
    summary = db.get_monthly_summary(user_id, now.year, now.month)
    balance = summary["income"] - summary["expense"]

    text = (
        "💰 *Manajemen Keuangan*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 *{MONTH_NAMES[now.month]} {now.year}*\n"
        f"💵 Pemasukan: *{fmt_rp(summary['income'])}*\n"
        f"💸 Pengeluaran: *{fmt_rp(summary['expense'])}*\n"
        f"💰 Saldo: *{fmt_rp(balance)}*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Pilih menu:"
    )
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=finance_menu_keyboard())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not db.default_categories_exist(user_id):
        db.seed_default_categories(user_id)

    text = (
        "🏠 *Menu Utama*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Pilih menu di bawah:"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=global_menu_keyboard())

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "❓ *Bantuan Finance Bot*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🤖 Bot ini membantu mencatat pemasukan & pengeluaran,\n"
        "melihat laporan bulanan, dan mengatur anggaran.\n\n"
        "📌 *Fitur:*\n"
        "├ 💰 *Catat Transaksi* — Tambah pemasukan/pengeluaran\n"
        "├ 📊 *Laporan* — Lihat rekap & grafik per bulan\n"
        "├ 🎯 *Anggaran* — Atur batas budget per kategori\n"
        "└ 📁 *Kategori* — Tambah/hapus kategori kustom\n\n"
        "📋 *Perintah Cepat:*\n"
        "├ /start — Buka menu utama\n"
        "├ /add — Catat transaksi\n"
        "├ /report — Laporan bulan ini\n"
        "├ /budget — Atur anggaran\n"
        "└ /categories — Kelola kategori"
    )
    if update.callback_query:
        q = update.callback_query
        await q.answer()
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=wrap_keyboard([]))
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=wrap_keyboard([]))

# ─── Catat Transaksi ────────────────────────────────────────

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💵 Pemasukan", callback_data="add_income")],
        [InlineKeyboardButton("💸 Pengeluaran", callback_data="add_expense")],
    ]
    msg = "📝 *Catat Transaksi*\n━━━━━━━━━━━━━━━━━━━━━━\nPilih tipe transaksi:"
    if update.callback_query:
        q = update.callback_query
        await q.answer()
        await q.edit_message_text(msg, parse_mode="Markdown", reply_markup=wrap_keyboard(keyboard))
    else:
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=wrap_keyboard(keyboard))
    return ADD_CHOICE

async def add_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "add_cancel":
        await query.edit_message_text("❌ Dibatalkan.", reply_markup=wrap_keyboard([]))
        return ConversationHandler.END
    context.user_data["add_type"] = data.split("_")[1]
    tipe = "Pemasukan" if context.user_data["add_type"] == "income" else "Pengeluaran"
    await query.edit_message_text(
        f"📝 *{tipe}*\n━━━━━━━━━━━━━━━━━━━━━━\nMasukkan jumlah (angka saja):\n\nContoh: `50000` atau `150.5`",
        parse_mode="Markdown",
    )
    return ADD_AMOUNT

async def add_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Masukkan angka yang valid. Contoh: `50000`", parse_mode="Markdown")
        return ADD_AMOUNT

    context.user_data["add_amount"] = amount
    typ = context.user_data["add_type"]
    categories = db.get_categories(update.effective_user.id, typ)
    keyboard = [
        [InlineKeyboardButton(cat["name"], callback_data=f"addcat_{cat['id']}")]
        for cat in categories
    ]
    await update.message.reply_text(
        "📂 *Pilih Kategori:*",
        parse_mode="Markdown",
        reply_markup=wrap_keyboard(keyboard),
    )
    return ADD_CATEGORY

async def add_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "addcat_cancel":
        await query.edit_message_text("❌ Dibatalkan.", reply_markup=wrap_keyboard([]))
        return ConversationHandler.END

    context.user_data["add_category_id"] = int(data.split("_")[1])
    await query.edit_message_text(
        "📝 *Catatan (opsional)*\n━━━━━━━━━━━━━━━━━━━━━━\nKetik catatan atau ketik `-` untuk skip:",
        parse_mode="Markdown",
    )
    return ADD_NOTE

async def add_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = update.message.text
    if note == "-":
        note = ""

    user_id = update.effective_user.id
    amount = context.user_data["add_amount"]
    typ = context.user_data["add_type"]
    category_id = context.user_data["add_category_id"]

    db.add_transaction(user_id, amount, typ, category_id, note)

    cat_name = next(
        (c["name"] for c in db.get_categories(user_id) if c["id"] == category_id),
        "Unknown",
    )

    emoji = "💵" if typ == "income" else "💸"
    tipe = "Pemasukan" if typ == "income" else "Pengeluaran"
    text = (
        f"✅ *Transaksi Tersimpan!*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{emoji} *{tipe}*\n"
        f"💰 Jumlah: *{fmt_rp(amount)}*\n"
        f"📂 Kategori: *{cat_name}*\n"
        f"📝 Catatan: *{note or '-'}*"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=wrap_keyboard([]))
    return ConversationHandler.END

# ─── Laporan ────────────────────────────────────────────────

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    is_cb = update.callback_query is not None
    await _show_report(update, context, now.year, now.month, is_callback=is_cb)

async def _show_report(update, context, year, month, is_callback=False):
    user_id = update.effective_user.id if not is_callback else update.callback_query.from_user.id
    summary = db.get_monthly_summary(user_id, year, month)
    transactions = db.get_monthly_report(user_id, year, month)
    spending = db.get_category_spending(user_id, year, month)
    month_str = f"{year:04d}-{month:02d}"
    budgets = db.get_budgets(user_id, month_str)

    income = summary["income"]
    expense = summary["expense"]
    balance = income - expense

    text = (
        f"📊 *Laporan {MONTH_NAMES[month]} {year}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 Pemasukan: *{fmt_rp(income)}*\n"
        f"💸 Pengeluaran: *{fmt_rp(expense)}*\n"
        f"💰 Saldo: *{fmt_rp(balance)}*\n\n"
    )

    if spending:
        text += "📂 *Per Kategori:*\n"
        for s in spending:
            cat_id, cat_name, total = s["id"], s["name"], s["total"]
            bar_len = max(1, int((total / max(expense, 1)) * 10))
            bar = "█" * bar_len + "░" * (10 - bar_len)
            text += f"  {bar} *{cat_name}*: {fmt_rp(total)}\n"

            for b in budgets:
                if b["category_id"] == cat_id:
                    rem = b["amount"] - total
                    if rem >= 0:
                        text += f"      ✅ Sisa budget: {fmt_rp(rem)}\n"
                    else:
                        text += f"      ⚠️ *Over budget!* Kelebihan {fmt_rp(abs(rem))}\n"
                    break
        text += "\n"

    if transactions:
        text += "📋 *Transaksi Terbaru:*\n"
        for i, t in enumerate(transactions[:8], 1):
            e = "💵" if t["type"] == "income" else "💸"
            s = "+" if t["type"] == "income" else "-"
            text += f"{i}. {t['date']} {e} *{t['category']}*: {s}{fmt_rp(abs(t['amount']))}\n"
        if len(transactions) > 8:
            text += f"     ...dan {len(transactions) - 8} transaksi lainnya\n"

    # Navigation buttons
    nav = []
    if year > 2020 or month > 1:
        pm = month - 1 if month > 1 else 12
        py = year if month > 1 else year - 1
        nav.append(InlineKeyboardButton(f"◀ {MONTH_NAMES[pm]}", callback_data=f"report_{py}_{pm}"))
    nav.append(InlineKeyboardButton("🔄 Bulan Ini", callback_data=f"report_{datetime.now().year}_{datetime.now().month}"))
    if year < 2030 or month < 12:
        nm = month + 1 if month < 12 else 1
        ny = year if month < 12 else year + 1
        nav.append(InlineKeyboardButton(f"{MONTH_NAMES[nm]} ▶", callback_data=f"report_{ny}_{nm}"))

    markup = InlineKeyboardMarkup([nav, menu_button()])

    if is_callback:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)

async def report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split("_")
    if len(parts) == 3 and parts[0] == "report":
        await _show_report(update, context, int(parts[1]), int(parts[2]), is_callback=True)

# ─── Budget ────────────────────────────────────────────────

async def budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if not update.callback_query else update.callback_query.from_user.id
    now = datetime.now()
    month_str = f"{now.year:04d}-{now.month:02d}"
    budgets = db.get_budgets(user_id, month_str)
    spending = db.get_category_spending(user_id, now.year, now.month)
    spend_map = {s["id"]: s["total"] for s in spending}

    text = (
        f"🎯 *Anggaran {MONTH_NAMES[now.month]} {now.year}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
    )

    if budgets:
        for b in budgets:
            spent = spend_map.get(b["category_id"], 0)
            rem = b["amount"] - spent
            pct = min(100, int((spent / max(b["amount"], 1)) * 100))
            bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
            status = f"✅ Sisa {fmt_rp(rem)}" if rem >= 0 else f"⚠️ *Over {fmt_rp(abs(rem))}*"
            text += f"📂 *{b['category']}*\n"
            text += f"  └ Anggaran: {fmt_rp(b['amount'])} | Terpakai: {fmt_rp(spent)}\n"
            text += f"  └ {bar} {pct}% — {status}\n\n"
    else:
        text += "Belum ada anggaran.\nGunakan tombol di bawah untuk menambah.\n"

    keyboard = [
        [InlineKeyboardButton("➕ Tambah Anggaran", callback_data="budget_add")],
        [InlineKeyboardButton("🗑 Hapus Anggaran", callback_data="budget_delete_list")],
    ]

    if update.callback_query:
        q = update.callback_query
        await q.answer()
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=wrap_keyboard(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=wrap_keyboard(keyboard))

async def budget_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "budget_add":
        cats = db.get_categories(update.effective_user.id, "expense")
        if not cats:
            await query.edit_message_text(
                "❌ Tidak ada kategori pengeluaran. Tambah dulu lewat menu Kategori.",
                reply_markup=wrap_keyboard([]),
            )
            return ConversationHandler.END

        keyboard = [[InlineKeyboardButton(c["name"], callback_data=f"bgtcat_{c['id']}")] for c in cats]
        await query.edit_message_text(
            "🎯 *Pilih Kategori untuk Anggaran:*",
            parse_mode="Markdown",
            reply_markup=wrap_keyboard(keyboard),
        )
        return BUDGET_AMOUNT

    elif data == "budget_delete_list":
        user_id = update.effective_user.id
        now = datetime.now()
        month_str = f"{now.year:04d}-{now.month:02d}"
        budgets = db.get_budgets(user_id, month_str)

        if not budgets:
            await query.edit_message_text(
                "Tidak ada anggaran untuk dihapus.",
                reply_markup=wrap_keyboard([]),
            )
            return ConversationHandler.END

        keyboard = [
            [InlineKeyboardButton(f"🗑 {b['category']} ({fmt_rp(b['amount'])})", callback_data=f"bgt_del_{b['id']}")]
            for b in budgets
        ]
        await query.edit_message_text(
            "🗑 *Pilih Anggaran yang Ingin Dihapus:*",
            parse_mode="Markdown",
            reply_markup=wrap_keyboard(keyboard),
        )
        return BUDGET_DELETE

    return ConversationHandler.END

async def budget_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "bgtcat_cancel":
        await query.edit_message_text("❌ Dibatalkan.", reply_markup=wrap_keyboard([]))
        return ConversationHandler.END
    context.user_data["budget_category_id"] = int(data.split("_")[1])
    await query.edit_message_text(
        "🎯 *Masukkan Jumlah Anggaran*\n━━━━━━━━━━━━━━━━━━━━━━\nKetik jumlah (angka saja):\n\nContoh: `1000000`",
        parse_mode="Markdown",
    )
    return BUDGET_AMOUNT

async def budget_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Masukkan angka yang valid. Contoh: `1000000`", parse_mode="Markdown")
        return BUDGET_AMOUNT

    user_id = update.effective_user.id
    category_id = context.user_data.get("budget_category_id")
    now = datetime.now()
    month_str = f"{now.year:04d}-{now.month:02d}"
    db.set_budget(user_id, category_id, month_str, amount)

    cat_name = next(
        (c["name"] for c in db.get_categories(user_id) if c["id"] == category_id),
        "Unknown",
    )
    await update.message.reply_text(
        f"✅ *Anggaran Disimpan!*\n━━━━━━━━━━━━━━━━━━━━━━\n📂 *{cat_name}*: {fmt_rp(amount)}",
        parse_mode="Markdown",
        reply_markup=wrap_keyboard([]),
    )
    return ConversationHandler.END

async def budget_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "bgt_del_cancel":
        await query.edit_message_text("❌ Dibatalkan.", reply_markup=wrap_keyboard([]))
        return ConversationHandler.END

    budget_id = int(data.split("_")[2])
    if db.delete_budget(update.effective_user.id, budget_id):
        await query.edit_message_text("✅ Anggaran berhasil dihapus!", reply_markup=wrap_keyboard([]))
    else:
        await query.edit_message_text("❌ Gagal menghapus anggaran.", reply_markup=wrap_keyboard([]))

    return ConversationHandler.END

# ─── Kategori ──────────────────────────────────────────────

async def categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if not update.callback_query else update.callback_query.from_user.id
    if not db.default_categories_exist(user_id):
        db.seed_default_categories(user_id)

    cats = db.get_categories(user_id)
    income_cats = [c for c in cats if c["type"] == "income"]
    expense_cats = [c for c in cats if c["type"] == "expense"]

    text = (
        "📁 *Kategori*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💵 *Pemasukan:*\n"
    )
    for c in income_cats:
        text += f"  • {c['name']}\n"
    text += f"\n💸 *Pengeluaran:*\n"
    for c in expense_cats:
        text += f"  • {c['name']}\n"

    keyboard = [
        [InlineKeyboardButton("➕ Tambah Kategori", callback_data="cat_add")],
        [InlineKeyboardButton("🗑 Hapus Kategori", callback_data="cat_delete")],
    ]

    if update.callback_query:
        q = update.callback_query
        await q.answer()
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=wrap_keyboard(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=wrap_keyboard(keyboard))

async def categories_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "cat_add":
        keyboard = [
            [InlineKeyboardButton("💵 Pemasukan", callback_data="catadd_income")],
            [InlineKeyboardButton("💸 Pengeluaran", callback_data="catadd_expense")],
        ]
        await query.edit_message_text(
            "📁 *Tambah Kategori Baru*\n━━━━━━━━━━━━━━━━━━━━━━\nPilih tipe kategori:",
            parse_mode="Markdown",
            reply_markup=wrap_keyboard(keyboard),
        )
        return CAT_ADD_NAME

    elif data == "cat_delete":
        cats = db.get_categories(update.effective_user.id)
        if not cats:
            await query.edit_message_text(
                "Tidak ada kategori untuk dihapus.",
                reply_markup=wrap_keyboard([]),
            )
            return ConversationHandler.END

        keyboard = [
            [InlineKeyboardButton(
                f"🗑 {c['name']} ({'💵' if c['type'] == 'income' else '💸'})",
                callback_data=f"catdel_{c['id']}",
            )]
            for c in cats
        ]
        await query.edit_message_text(
            "🗑 *Pilih Kategori yang Ingin Dihapus:*",
            parse_mode="Markdown",
            reply_markup=wrap_keyboard(keyboard),
        )
        return CAT_DELETE

    return ConversationHandler.END

async def cat_add_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "catadd_cancel":
        await query.edit_message_text("❌ Dibatalkan.", reply_markup=wrap_keyboard([]))
        return ConversationHandler.END

    context.user_data["cat_add_type"] = data.split("_")[1]
    await query.edit_message_text(
        "📁 *Nama Kategori Baru*\n━━━━━━━━━━━━━━━━━━━━━━\nKetik nama kategori:",
        parse_mode="Markdown",
    )
    return CAT_ADD_NAME

async def cat_add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("❌ Nama tidak boleh kosong.")
        return CAT_ADD_NAME

    user_id = update.effective_user.id
    typ = context.user_data.get("cat_add_type")

    result = db.add_category(user_id, name, typ)
    if result is None:
        await update.message.reply_text(
            f"❌ Kategori *'{name}'* sudah ada.",
            parse_mode="Markdown",
            reply_markup=wrap_keyboard([]),
        )
    else:
        await update.message.reply_text(
            f"✅ Kategori *'{name}'* berhasil ditambahkan!",
            parse_mode="Markdown",
            reply_markup=wrap_keyboard([]),
        )
    return ConversationHandler.END

async def cat_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "catdel_cancel":
        await query.edit_message_text("❌ Dibatalkan.", reply_markup=wrap_keyboard([]))
        return ConversationHandler.END

    category_id = int(data.split("_")[1])
    if db.delete_category(update.effective_user.id, category_id):
        await query.edit_message_text("✅ Kategori berhasil dihapus!", reply_markup=wrap_keyboard([]))
    else:
        await query.edit_message_text("❌ Gagal menghapus kategori.", reply_markup=wrap_keyboard([]))
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Dibatalkan.", reply_markup=wrap_keyboard([]))
    return ConversationHandler.END
