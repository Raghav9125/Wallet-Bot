import html
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

from database import Database
from keyboards.user_keyboards import (
    cancel_keyboard,
    main_menu,
    services_menu,
    understood_menu,
    whatsapp_button,
)
from utils.constants import STATUS_LABELS
from utils.validators import is_valid_utr, normalize_utr

WAITING_RECEIPT, WAITING_UTR = range(2)

GOOGLE_DOCS = [
    "Mobile Number",
    "Gmail ID",
    "Aadhaar Card",
    "PAN Card",
    "Bank Account Details",
    "IFSC Code",
]

COMMON_DOCS = [
    "Mobile Number",
    "Aadhaar Card",
    "PAN Card",
    "Bank Account Details",
    "IFSC Code",
]


def _db(context: ContextTypes.DEFAULT_TYPE) -> Database:
    return context.application.bot_data["db"]


async def _replace_callback_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    *,
    reply_markup=None,
    parse_mode=None,
) -> None:
    """Safely replace either a text message or a photo/caption message."""
    query = update.callback_query
    if not query or not query.message:
        return

    try:
        await query.delete_message()
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=text,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = _db(context)
    channel = db.get_setting("channel_link", "https://t.me/")
    image = db.get_setting("welcome_image_file_id", "")
    first_name = html.escape(update.effective_user.first_name if update.effective_user else "User")
    india_now = datetime.now(ZoneInfo("Asia/Kolkata"))
    current_date = india_now.strftime("%d %B %Y")
    current_minutes = india_now.hour * 60 + india_now.minute
    opening_minutes = 10 * 60
    closing_minutes = 21 * 60 + 30

    if opening_minutes <= current_minutes <= closing_minutes:
        availability_text = "✅ <b>Service Available</b>"
    else:
        availability_text = "🌙 <b>Come Back Again Tomorrow at 10:00 AM</b>"

    text = (
        f"👋 <b>Hello {first_name}!</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🎉 <b>India Business Wallets</b>\n\n"
        "💳 <b>Business Wallet Services</b>\n"
        "📝 Apply Now & Track Status\n\n"
        "🕙 <b>Working Hours</b>\n"
        "10:00 AM – 9:30 PM\n\n"
        f"{availability_text}\n"
        f"📅 <b>{current_date}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Neeche diye gaye button se service select karein 👇"
    )
    if update.callback_query:
        try:
            await update.callback_query.delete_message()
        except Exception:
            pass
    if image:
        try:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id, photo=image, caption=text,
                parse_mode=ParseMode.HTML, reply_markup=main_menu(channel)
            )
            return
        except Exception:
            pass
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=text,
        parse_mode=ParseMode.HTML, reply_markup=main_menu(channel)
    )


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = _db(context)
    data = query.data or ""

    if data == "user:home":
        return await start(update, context)

    if data == "user:apply":
        services = db.list_services(active_only=False)
        await _replace_callback_message(
            update,
            context,
            "💼 <b>Aap kaunsa Business Wallet open karna chahte hain?</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=services_menu(services),
        )
        return

    if data == "user:support":
        link = db.get_setting("whatsapp_link", "https://wa.me/")
        support_text = html.escape(db.get_setting("support_text"))
        await _replace_callback_message(
            update,
            context,
            f"💬 <b>Support</b>\n\n{support_text}",
            parse_mode=ParseMode.HTML,
            reply_markup=whatsapp_button(link),
        )
        return

    if data == "user:status":
        apps = db.get_user_applications(query.from_user.id)
        if not apps:
            await _replace_callback_message(
                update,
                context,
                "Aapki koi application nahi mili.",
                reply_markup=main_menu(db.get_setting("channel_link")),
            )
            return
        lines = ["🔍 <b>Your Applications</b>\n"]
        for app in apps:
            status = STATUS_LABELS.get(app["status"], app["status"])
            lines.append(
                f"<b>{html.escape(app['application_no'])}</b>\n"
                f"Service: {html.escape(app['service_name'])}\n"
                f"Amount: ₹{app['amount']}\n"
                f"Status: {status}\n"
            )
        await _replace_callback_message(
            update,
            context,
            "\n".join(lines),
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu(db.get_setting("channel_link")),
        )
        return

    if data.startswith("svc:"):
        code = data.split(":", 1)[1]
        service = db.get_service(code)
        if not service:
            await _replace_callback_message(update, context, "Service nahi mili.")
            return
        if not service["active"]:
            await query.edit_message_text(
                f"❌ <b>{html.escape(service['name'])}</b> abhi available nahi hai.\n\nSupport se contact karein.",
                parse_mode=ParseMode.HTML,
                reply_markup=whatsapp_button(db.get_setting("whatsapp_link", "https://wa.me/")),
            )
            return
        docs = GOOGLE_DOCS if code == "google_pay" else COMMON_DOCS
        doc_text = "\n".join(f"• {html.escape(item)}" for item in docs)
        await _replace_callback_message(
            update,
            context,
            f"💳 <b>{html.escape(service['name'])}</b>\n\n"
            f"<b>Required Documents:</b>\n{doc_text}\n\n"
            f"<b>Service Charge:</b> ₹{service['price']}\n\n"
            "Payment karne se pehle details dhyan se padh lein.",
            parse_mode=ParseMode.HTML,
            reply_markup=understood_menu(code),
        )
        return

    if data.startswith("understood:"):
        code = data.split(":", 1)[1]
        service = db.get_service(code, active_only=True)
        if not service:
            await query.edit_message_text("❌ Ye service abhi available nahi hai.")
            return ConversationHandler.END

        context.user_data["service_code"] = code
        context.user_data["service_name"] = service["name"]
        context.user_data["amount"] = service["price"]

        qr_file_id = db.get_setting("qr_file_id")
        upi_id = html.escape(db.get_setting("upi_id", "Not set"))
        payment_name = html.escape(db.get_setting("payment_name", "India Business Wallet"))
        caption = (
            f"💳 <b>Payment Details</b>\n\n"
            f"Service: {html.escape(service['name'])}\n"
            f"Amount: ₹{service['price']}\n"
            f"UPI ID: <code>{upi_id}</code>\n"
            f"Account Name: {payment_name}\n\n"
            "Payment complete karne ke baad receipt ka clear screenshot bhejein."
        )

        try:
            await query.delete_message()
        except Exception:
            pass

        if qr_file_id:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=qr_file_id,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=cancel_keyboard(),
            )
        else:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=caption + "\n\n⚠️ Admin ne QR code abhi set nahi kiya hai.",
                parse_mode=ParseMode.HTML,
                reply_markup=cancel_keyboard(),
            )
        return WAITING_RECEIPT

    if data == "user:cancel":
        context.user_data.clear()
        await query.edit_message_text("Application process cancel kar diya gaya.")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Main menu:",
            reply_markup=main_menu(db.get_setting("channel_link")),
        )
        return ConversationHandler.END


async def receive_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo:
        await update.message.reply_text(
            "Kripya payment receipt ka screenshot photo ke roop me bhejein.",
            reply_markup=cancel_keyboard(),
        )
        return WAITING_RECEIPT

    context.user_data["receipt_file_id"] = update.message.photo[-1].file_id
    await update.message.reply_text(
        "✅ Receipt mil gayi.\n\nAb payment ka UTR/Transaction Reference Number bhejein.",
        reply_markup=cancel_keyboard(),
    )
    return WAITING_UTR


async def receive_utr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = _db(context)
    raw = (update.message.text or "").strip()
    if not is_valid_utr(raw):
        await update.message.reply_text(
            "UTR invalid lag raha hai. 6–30 letters/numbers ka valid UTR bhejein."
        )
        return WAITING_UTR

    utr = normalize_utr(raw)
    if db.application_exists_by_utr(utr):
        await update.message.reply_text(
            "❌ Ye UTR pehle hi submit ho chuka hai. Kripya payment verify karke sahi UTR bhejein."
        )
        return WAITING_UTR

    required = ("service_code", "service_name", "amount", "receipt_file_id")
    if any(key not in context.user_data for key in required):
        context.user_data.clear()
        await update.message.reply_text(
            "Session expire ho gaya. Kripya /start karke dobara apply karein."
        )
        return ConversationHandler.END

    user = update.effective_user
    app_no = db.create_application(
        user_id=user.id,
        full_name=user.full_name,
        username=user.username,
        service_code=context.user_data["service_code"],
        service_name=context.user_data["service_name"],
        amount=context.user_data["amount"],
        receipt_file_id=context.user_data["receipt_file_id"],
        utr=utr,
    )
    app = db.get_application(app_no)

    await update.message.reply_text(
        "✅ <b>Application successfully submitted</b>\n\n"
        f"Application ID: <code>{app_no}</code>\n"
        f"Service: {html.escape(app['service_name'])}\n"
        f"Amount: ₹{app['amount']}\n"
        f"Status: {STATUS_LABELS['PAYMENT_PENDING']}\n\n"
        "Verification ke baad status update kiya jayega.",
        parse_mode=ParseMode.HTML,
        reply_markup=whatsapp_button(db.get_setting("whatsapp_link")),
    )

    admin_ids = context.application.bot_data["admin_ids"]
    from keyboards.admin_keyboards import application_actions

    username = f"@{user.username}" if user.username else "Not available"
    admin_caption = (
        "🆕 <b>New Payment Application</b>\n\n"
        f"Application: <code>{app_no}</code>\n"
        f"User: {html.escape(user.full_name)}\n"
        f"Username: {html.escape(username)}\n"
        f"User ID: <code>{user.id}</code>\n"
        f"Service: {html.escape(app['service_name'])}\n"
        f"Amount: ₹{app['amount']}\n"
        f"UTR: <code>{html.escape(utr)}</code>\n"
        f"Status: {STATUS_LABELS['PAYMENT_PENDING']}"
    )
    for admin_id in admin_ids:
        try:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=app["receipt_file_id"],
                caption=admin_caption,
                parse_mode=ParseMode.HTML,
                reply_markup=application_actions(app_no),
            )
        except Exception:
            pass

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Application cancel kar di gayi.",
        reply_markup=main_menu(_db(context).get_setting("channel_link")),
    )
    return ConversationHandler.END
