import os
import random
import logging
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
import config
import ai
import db

logging.basicConfig(level=logging.INFO)
os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)

# Conversation states
WAITING_MEDIA, WAITING_LOCATION, WAITING_CONSENT = range(3)

GREETINGS = {
  "en": "Namaste 🙏 I'm Setu. I help get problems near you *seen and solved* — a broken school toilet, dirty water, an unsafe road. Want to report one?",
  "hi": "नमस्ते 🙏 मैं सेतु हूँ। मैं आपके आस-पास की समस्याओं को *सामने लाने और हल कराने* में मदद करता हूँ — टूटा शौचालय, गंदा पानी, असुरक्षित सड़क। क्या आप एक समस्या बताना चाहेंगे?",
  "bn": "নমস্কার 🙏 আমি সেতু। আপনার আশেপাশের সমস্যা *তুলে ধরতে ও সমাধান করতে* সাহায্য করি। একটি সমস্যা জানাতে চান?",
  "ta": "வணக்கம் 🙏 நான் சேது. உங்கள் பகுதியில் உள்ள பிரச்சினைகளை *வெளிக்கொணர்ந்து தீர்க்க* உதவுகிறேன். ஒன்றைப் பதிவு செய்ய விரும்புகிறீர்களா?",
  "te": "నమస్తే 🙏 నేను సేతు. మీ చుట్టుపక్కల సమస్యలను *గుర్తించి పరిష్కరించడంలో* సహాయపడతాను. ఒకదాన్ని నివేదించాలా?",
  "kn": "ನಮಸ್ಕಾರ 🙏 ನಾನು ಸೇತು. ನಿಮ್ಮ ಸುತ್ತಮುತ್ತಲ ಸಮಸ್ಯೆಗಳನ್ನು *ಗುರುತಿಸಿ ಪರಿಹರಿಸಲು* ಸಹಾಯ ಮಾಡುತ್ತೇನೆ. ಒಂದನ್ನು ವರದಿ ಮಾಡಬೇಕೆ?"
}

WHAT_IS_SETU = ("सेतु / Setu is a free bridge between the problems around you and the people who can fix them. "
  "You speak a problem — in any language, by voice if you like — and we put it on a public map, "
  "sort what companies can fund vs. what's the government's job, and help get it solved. "
  "We never show your name. We take ₹0 from any help.")

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗣️ Report a problem", callback_data="menu_report")],
        [InlineKeyboardButton("❓ What is Setu?", callback_data="menu_about")],
        [InlineKeyboardButton("🗺️ See the map", url="https://setu-map.vercel.app")],
    ])

GOV_CHANNELS = {
  "default": {
    "name": "MCD 311 (Delhi)",
    "url": "https://mcd311.example/complaint",
    "note": "garbage, drains, streetlights, sewer overflow"
  }
}


def make_handle() -> str:
    return f"Citizen#{random.randint(1000, 9999)}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Namaste 🙏 I am Setu.\n\n"
        "Send me a *voice note*, *video*, or *photo* of any civic or development "
        "problem near you — a broken school toilet, a dirty lake, a dangerous road, "
        "poisoned water. Speak in any language.\n\nGo ahead, send it now.",
        parse_mode="Markdown",
    )
    return WAITING_MEDIA


async def receive_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.voice:
        tg_file, media_type, ext = msg.voice, "audio", "ogg"
    elif msg.audio:
        tg_file, media_type, ext = msg.audio, "audio", "mp3"
    elif msg.video:
        tg_file, media_type, ext = msg.video, "video", "mp4"
    elif msg.photo:
        tg_file, media_type, ext = msg.photo[-1], "photo", "jpg"
    else:
        await msg.reply_text("Please send a voice note, video, or photo.")
        return WAITING_MEDIA

    await msg.reply_text("Got it. Uploading… ⏳")
    f = await tg_file.get_file()
    local_path = os.path.join(config.DOWNLOAD_DIR, f"{tg_file.file_id}.{ext}")
    await f.download_to_drive(local_path)
    media_url = db.upload_media(local_path, media_type)
    os.remove(local_path)

    context.user_data["media_type"] = media_type
    context.user_data["media_url"] = media_url
    context.user_data["local_for_ai"] = media_url  # used later via re-download if needed
    context.user_data["caption"] = msg.caption or ""

    # For AI we need the raw audio; re-download path kept simple: store the file id
    context.user_data["tg_file_id"] = tg_file.file_id
    context.user_data["ext"] = ext

    loc_btn = KeyboardButton("📍 Share location", request_location=True)
    await msg.reply_text(
        "Now share the *location* of this problem so it can appear on the map.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([[loc_btn]], one_time_keyboard=True, resize_keyboard=True),
    )
    return WAITING_LOCATION


async def receive_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loc = update.message.location
    if not loc:
        await update.message.reply_text("Please tap the 📍 Share location button.")
        return WAITING_LOCATION
    context.user_data["latitude"] = loc.latitude
    context.user_data["longitude"] = loc.longitude

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, I agree", callback_data="consent_yes")],
        [InlineKeyboardButton("❌ No", callback_data="consent_no")],
    ])
    await update.message.reply_text(
        "Last step. May we:\n"
        "(a) show this problem publicly on the map *without your name*, and\n"
        "(b) message you privately to confirm when it is fixed?",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    await update.message.reply_text("Please choose:", reply_markup=buttons)
    return WAITING_CONSENT


async def receive_consent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "consent_no":
        await query.edit_message_text(
            "Understood. We will not post this. Thank you for trying. Send /start anytime."
        )
        context.user_data.clear()
        return ConversationHandler.END

    await query.edit_message_text("🙏 Thank you. Processing your report…")

    # Re-download media for AI (audio/video only)
    transcript, language = "", "unknown"
    media_type = context.user_data["media_type"]
    if media_type in ("audio", "video"):
        tg_file = await context.bot.get_file(context.user_data["tg_file_id"])
        ai_path = os.path.join(config.DOWNLOAD_DIR, f"ai_{context.user_data['tg_file_id']}.{context.user_data['ext']}")
        await tg_file.download_to_drive(ai_path)
        try:
            tr = ai.transcribe(ai_path)
            transcript, language = tr["text"], tr["language"]
        except Exception as e:
            logging.error(f"Transcription failed: {e}")
            transcript = context.user_data.get("caption", "")
        finally:
            if os.path.exists(ai_path):
                os.remove(ai_path)
    else:
        transcript = context.user_data.get("caption", "Photo report (no text).")

    source_text = transcript or context.user_data.get("caption", "")
    try:
        s = ai.structure(source_text) if source_text.strip() else {
            "title": "Photo report", "description": "Citizen submitted a photo.",
            "category": "other", "legality_bin": "reframe", "severity": "medium",
        }
    except Exception as e:
        logging.error(f"Structuring failed: {e}")
        s = {"title": "Report (needs review)", "description": source_text[:200] or "Manual review needed.",
             "category": "other", "legality_bin": "reframe", "severity": "medium"}

    handle = make_handle()
    record = {
        "reporter_telegram_id": query.from_user.id,
        "reporter_handle": handle,
        "media_type": media_type,
        "media_url": context.user_data["media_url"],
        "transcript": transcript,
        "detected_language": language,
        "title": s["title"],
        "description": s["description"],
        "category": s["category"],
        "legality_bin": s["legality_bin"],
        "severity": s["severity"],
        "latitude": context.user_data["latitude"],
        "longitude": context.user_data["longitude"],
        "consent_public": True,
        "consent_contact": True,
        "status": "pending_review",
    }
    if s["legality_bin"] == "statutory":
        record["gov_status"] = "routed"
        record["gov_days"] = 0
    problem_id = db.insert_problem(record)

    await context.bot.send_message(
        chat_id=query.from_user.id,
        text="🙏 Thank you. Your report has been received and is being reviewed. "
             "We'll notify you here when it goes live. Your name is never shown publicly.",
    )

    # Assisted gov routing for statutory wounds
    if s["legality_bin"] == "statutory":
        try:
            await send_gov_routing(context, query.from_user.id, record)
        except Exception as e:
            logging.error(f"Gov routing message failed: {e}")

    # Notify admin with approve/reject buttons
    bin_emoji = {"fundable": "💚", "statutory": "🏛️", "reframe": "✂️"}.get(s["legality_bin"], "❓")
    maps_link = f"https://www.google.com/maps?q={record['latitude']},{record['longitude']}"
    admin_text = (
        f"🆕 *New report* ({handle})\n\n"
        f"*Title:* {s['title']}\n"
        f"*Desc:* {s['description']}\n"
        f"*Category:* {s['category']}\n"
        f"*Bin:* {bin_emoji} {s['legality_bin']}\n"
        f"*Severity:* {s['severity']}\n"
        f"*Lang:* {language}\n"
        f"*Location:* [open map]({maps_link})\n"
        f"*Media:* [view]({record['media_url']})"
    )
    admin_buttons = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve & Publish", callback_data=f"approve|{problem_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject|{problem_id}"),
    ]])
    await context.bot.send_message(
        chat_id=config.ADMIN_TELEGRAM_ID, text=admin_text,
        parse_mode="Markdown", reply_markup=admin_buttons,
        disable_web_page_preview=True,
    )
    context.user_data.clear()
    return ConversationHandler.END


async def admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, problem_id = query.data.split("|", 1)
    if action == "approve":
        db.update_status(problem_id, "published")
        await query.edit_message_text(query.message.text_markdown + "\n\n✅ *PUBLISHED*",
                                      parse_mode="Markdown", disable_web_page_preview=True)
        # fetch reporter to notify
        row = db.supabase.table("problems").select("reporter_telegram_id").eq("id", problem_id).execute()
        if row.data and row.data[0]["reporter_telegram_id"]:
            try:
                await context.bot.send_message(
                    chat_id=row.data[0]["reporter_telegram_id"],
                    text="✅ Your report is now live on the Setu map. Thank you for speaking up. 🙏",
                )
            except Exception:
                pass
    else:
        db.update_status(problem_id, "rejected")
        await query.edit_message_text(query.message.text_markdown + "\n\n❌ *REJECTED*",
                                      parse_mode="Markdown", disable_web_page_preview=True)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Cancelled. Send /start to begin again.",
                                    reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def greet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    lang = ai.detect_greeting_language(text)
    await update.message.reply_text(
        GREETINGS.get(lang, GREETINGS["en"]),
        parse_mode="Markdown", reply_markup=main_menu()
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WHAT_IS_SETU, reply_markup=main_menu())


async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "menu_about":
        await q.message.reply_text(WHAT_IS_SETU, reply_markup=main_menu())


async def menu_start_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.message.reply_text(
        "Wonderful 🙏 Send me a *voice note*, *photo*, or *video* of the problem. Speak in any language.",
        parse_mode="Markdown")
    return WAITING_MEDIA


async def send_gov_routing(context, chat_id, problem):
    ch = GOV_CHANNELS["default"]
    prefilled = (f"Civic complaint: {problem['title']}. {problem['description']} "
                 f"Location: approx {problem['latitude']:.4f},{problem['longitude']:.4f}.")
    btns = InlineKeyboardMarkup([[InlineKeyboardButton(f"📨 File with {ch['name']}", url=ch["url"])]])
    await context.bot.send_message(
        chat_id=chat_id,
        text=("🏛️ This problem is the *government's legal duty* (e.g. "+ch["note"]+"), so companies cannot fund it. "
              "But you can file it with the official channel in one tap — we've written it for you:\n\n"
              f"`{prefilled}`\n\n"
              "We'll keep it on the Setu map as *routed & tracked* so it's never invisible."),
        parse_mode="Markdown", reply_markup=btns)


def main():
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(menu_start_report, pattern="^menu_report$"),
        ],
        states={
            WAITING_MEDIA: [MessageHandler(
                filters.VOICE | filters.AUDIO | filters.VIDEO | filters.PHOTO, receive_media)],
            WAITING_LOCATION: [MessageHandler(filters.LOCATION, receive_location)],
            WAITING_CONSENT: [CallbackQueryHandler(receive_consent, pattern="^consent_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(admin_decision, pattern="^(approve|reject)\\|"))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(menu_router, pattern="^menu_"))
    # Catch-all greeting: only for text that isn't part of an active conversation.
    # group=1 ensures the ConversationHandler (default group=0) takes precedence.
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, greet), group=1)
    logging.info("Setu bot running (polling)…")
    app.run_polling()


if __name__ == "__main__":
    main()
