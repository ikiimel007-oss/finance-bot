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

KEGIATAN_TAMBAH, KEGIATAN_HAPUS = range(30, 32)

BULAN_INDO = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]
HARI_INDO = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def get_hari_ini():
    return HARI_INDO[datetime.now().weekday()]

def get_bulan_tahun_ini():
    now = datetime.now()
    return f"{BULAN_INDO[now.month - 1]}-{now.year}"

def progress_bar(selesai, total, panjang=10):
    if total == 0:
        return "░" * panjang
    isi = round(selesai / total * panjang)
    return "█" * isi + "░" * (panjang - isi)

def statistik(kegiatan):
    total = len(kegiatan)
    selesai = sum(1 for k in kegiatan if k["done"])
    persen = round(selesai / total * 100) if total else 0
    return total, selesai, persen


def menu_button_keg():
    return [InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_main")]

def back_button_keg():
    return [InlineKeyboardButton("◀️ Kembali", callback_data="menu_kegiatan")]

def wrap_keyboard_keg(buttons):
    return InlineKeyboardMarkup(buttons + [back_button_keg(), menu_button_keg()])


def kegiatan_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Daftar Kegiatan", callback_data="keg_daftar")],
        [InlineKeyboardButton("➕ Tambah Kegiatan", callback_data="keg_tambah")],
        [InlineKeyboardButton("❌ Hapus Kegiatan", callback_data="keg_hapus")],
        [InlineKeyboardButton("📅 Laporan Hari Ini", callback_data="keg_laporan_harian")],
        [InlineKeyboardButton("📅 Laporan Bulan Ini", callback_data="keg_laporan_bulanan")],
        back_button_keg(),
        menu_button_keg(),
    ])


async def kegiatan_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "📋 *Menu Kegiatan*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Pilih menu di bawah:"
    )
    try:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kegiatan_menu_keyboard())
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise


# ─── DAFTAR KEGIATAN ─────────────────────────────────────

def _build_kegiatan_list(chat_id):
    kegiatan = db.get_kegiatan(chat_id)
    if not kegiatan:
        return None, None
    total, selesai, persen = statistik(kegiatan)
    text = (
        f"📋 *Daftar Kegiatan*\n"
        f"├─ Total: {total} kegiatan\n"
        f"├─ Selesai: {selesai} ✅\n"
        f"└─ Progress: {persen}%\n"
        f"`{progress_bar(selesai, total)}`\n\n"
        f"_Klik tombol di bawah untuk tandai selesai/belum._"
    )
    buttons = []
    for k in kegiatan:
        ikon = "✅" if k["done"] else "⬜"
        buttons.append([
            InlineKeyboardButton(
                f"{k['id']}. {ikon} [{k['day']}] {k['text']}",
                callback_data=f"keg_toggle_{k['id']}",
            )
        ])
    buttons.append(back_button_keg())
    buttons.append(menu_button_keg())
    return text, InlineKeyboardMarkup(buttons)

async def keg_daftar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    text, keyboard = _build_kegiatan_list(chat_id)
    if text is None:
        await query.edit_message_text(
            "🌱 *Belum ada kegiatan.*\nGunakan ➕ Tambah Kegiatan untuk mulai!",
            parse_mode="Markdown",
            reply_markup=wrap_keyboard_keg([]),
        )
        return
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)


# ─── TOGGLE ───────────────────────────────────────────────

async def keg_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    kegiatan_id = int(query.data.split("_")[2])
    db.toggle_kegiatan(kegiatan_id)

    chat_id = query.message.chat.id
    kegiatan = db.get_kegiatan(chat_id)
    total, selesai, persen = statistik(kegiatan)
    status_text = "Selesai ✅" if any(k["id"] == kegiatan_id and k["done"] for k in kegiatan) else "Belum ⬜"
    await query.answer(f"{status_text} • Progress: {persen}%")

    text, keyboard = _build_kegiatan_list(chat_id)
    if text:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)


# ─── TAMBAH ───────────────────────────────────────────────

async def keg_tambah_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "✍️ *Tulis kegiatan:*\n"
        "• Pisahkan tiap kegiatan dengan *enter*\n"
        "• Gunakan `|` lalu hari, contoh: `Belajar|Senin`\n"
        "• Jika hari dikosongkan, otomatis hari ini.\n\n"
        "_Kirim sekarang:_",
        parse_mode="Markdown",
        reply_markup=wrap_keyboard_keg([]),
    )
    return KEGIATAN_TAMBAH


async def keg_tambah_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    jumlah = 0
    for line in update.message.text.split("\n"):
        parts = line.split("|")
        teks = parts[0].strip()
        if not teks:
            continue
        hari = parts[1].strip().capitalize() if len(parts) > 1 and parts[1].strip() else get_hari_ini()
        db.add_kegiatan(chat_id, teks, hari, get_bulan_tahun_ini())
        jumlah += 1

    if jumlah == 0:
        await update.message.reply_text("⚠️ Tidak ada kegiatan yang ditambahkan (input kosong).")
        return ConversationHandler.END

    await update.message.reply_text(
        f"🎉 Berhasil menambahkan *{jumlah}* kegiatan! Semangat ya! 💪",
        parse_mode="Markdown",
        reply_markup=kegiatan_menu_keyboard(),
    )
    return ConversationHandler.END


# ─── HAPUS ────────────────────────────────────────────────

async def keg_hapus_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    kegiatan = db.get_kegiatan(chat_id)
    if not kegiatan:
        await query.edit_message_text(
            "🌱 Belum ada kegiatan yang bisa dihapus.",
            reply_markup=wrap_keyboard_keg([]),
        )
        return ConversationHandler.END

    text = "🔢 *Balas dengan nomor urut* kegiatan yang ingin dihapus:\n\n"
    for i, k in enumerate(kegiatan, 1):
        text += f"{i}. {k['text']} ({k['day']})\n"

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=wrap_keyboard_keg([]))
    return KEGIATAN_HAPUS


async def keg_hapus_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    try:
        idx = int(update.message.text.strip()) - 1
    except ValueError:
        await update.message.reply_text("⚠️ Mohon balas dengan *angka* (contoh: 1).", parse_mode="Markdown")
        return KEGIATAN_HAPUS

    kegiatan = db.get_kegiatan(chat_id)
    if idx < 0 or idx >= len(kegiatan):
        await update.message.reply_text("⚠️ Nomor tidak ditemukan.", reply_markup=kegiatan_menu_keyboard())
        return ConversationHandler.END

    target = kegiatan[idx]
    db.delete_kegiatan(target["id"])
    await update.message.reply_text(
        f"🗑️ Kegiatan *{target['text']}* berhasil dihapus.",
        parse_mode="Markdown",
        reply_markup=kegiatan_menu_keyboard(),
    )
    return ConversationHandler.END


# ─── LAPORAN ──────────────────────────────────────────────

def blok_laporan(judul, kegiatan):
    total, selesai, persen = statistik(kegiatan)
    baris = "\n".join(f"{'✅' if k['done'] else '⬜'} {k['text']}" for k in kegiatan)
    return (
        f"{judul}\n"
        f"├─ Selesai: {selesai}/{total}\n"
        f"└─ Progress: {persen}%\n"
        f"`{progress_bar(selesai, total)}`\n\n"
        f"{baris}"
    )


async def keg_laporan_harian(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    hari_ini = get_hari_ini()
    kegiatan = db.get_kegiatan_by_day(chat_id, hari_ini)
    if not kegiatan:
        await query.edit_message_text(
            f"📅 *Laporan {hari_ini}*\n\nTidak ada kegiatan untuk hari ini. 😴",
            parse_mode="Markdown",
            reply_markup=wrap_keyboard_keg([]),
        )
        return

    await query.edit_message_text(
        blok_laporan(f"📅 *Laporan Harian — {hari_ini}*", kegiatan),
        parse_mode="Markdown",
        reply_markup=wrap_keyboard_keg([]),
    )


async def keg_laporan_bulanan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    bulan_ini = get_bulan_tahun_ini()
    kegiatan = db.get_kegiatan_by_month(chat_id, bulan_ini)
    if not kegiatan:
        await query.edit_message_text(
            f"📅 *Laporan {bulan_ini}*\n\nBelum ada kegiatan tercatat bulan ini. ✍️",
            parse_mode="Markdown",
            reply_markup=wrap_keyboard_keg([]),
        )
        return

    await query.edit_message_text(
        blok_laporan(f"📆 *Laporan Bulanan — {bulan_ini}*", kegiatan),
        parse_mode="Markdown",
        reply_markup=wrap_keyboard_keg([]),
    )
