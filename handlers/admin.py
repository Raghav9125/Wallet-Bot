import html
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

from database import Database
from keyboards.admin_keyboards import (
    admin_menu,
    application_actions,
    availability_services_menu,
    price_services_menu,
)
from utils.constants import STATUS_LABELS

WAITING_SETTING, WAITING_PRICE, WAITING_REJECT_REASON = range(10, 13)


def _db(context: ContextTypes.DEFAULT_TYPE) -> Database:
    return context.application.bot_data["db"]


def _is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    return bool(update.effective_user and update.effective_user.id in context.application.bot_data["admin_ids"])


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update, context):
        await update.message.reply_text("â›” Aap admin nahi hain.")
        return
    await update.message.reply_text(
        "ðŸ›  <b>India Business Wallet Admin Panel</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_menu(),
    )


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not _is_admin(update, context):
        await query.answer("Admin access required.", show_alert=True)
        return ConversationHandler.END

    db = _db(context)
    data = query.data or ""

    if data == "admin:home":
        await query.edit_message_text(
            "ðŸ›  <b>India Business Wallet Admin Panel</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_menu(),
        )
        return ConversationHandler.END

    if data == "admin:stats":
        s = db.stats()
        await query.edit_message_text(
            "ðŸ“ˆ <b>Application Statistics</b>\n\n"
            f"Total: {s['total']}\n"
            f"Pending: {s['pending']}\n"
            f"Successful: {s['success']}\n"
            f"Rejected: {s['rejected']}",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_menu(),
        )
        return ConversationHandler.END

    if data == "admin:prices":
        await query.edit_message_text(
            "ðŸ’° Price change karne ke liye service select karein:",
            reply_markup=price_services_menu(db.list_services(active_only=False)),
        )
        return ConversationHandler.END

    if data == "admin:availability":
        await query.edit_message_text(
            "ðŸŸ¢ <b>Service Availability</b>\n\nStatus badalne ke liye service par tap karein.",
            parse_mode=ParseMode.HTML,
            reply_markup=availability_services_menu(db.list_services(active_only=False)),
        )
        return ConversationHandler.END

    if data.startswith("admin:toggle:"):
        code = data.split(":", 2)[2]
        service = db.get_service(code)
        if not service:
            await query.answer("Service nahi mili.", show_alert=True)
            return ConversationHandler.END
        new_active = not bool(service["active"])
        db.set_service_active(code, new_active)
        await query.answer("Status updated.", show_alert=True)
        await query.edit_message_text(
            "ðŸŸ¢ <b>Service Availability</b>\n\nStatus badalne ke liye service par tap karein.",
            parse_mode=ParseMode.HTML,
            reply_markup=availability_services_menu(db.list_services(active_only=False)),
        )
        return ConversationHandler.END

    if data.startswith("admin:price:"):
        code = data.split(":", 2)[2]
        service = db.get_service(code)
        if not service:
            await query.edit_message_text("Service nahi mili.", reply_markup=admin_menu())
            return ConversationHandler.END
        context.user_data["admin_action"] = "price"
        context.user_data["service_code"] = code
        context.user_data["service_name"] = service["name"]
        await query.edit_message_text(
            f"{service['name']} ka naya price sirf number me bhejein.\nExample: 1500"
        )
        return WAITING_PRICE

    if data == "admin:set:qr":
        context.user_data["admin_action"] = "qr_file_id"
        await query.edit_message_text("Naya payment QR code photo ke roop me bhejein.")
        return WAITING_SETTING

    if data == "admin:set:welcome_image":
        context.user_data["admin_action"] = "welcome_image_file_id"
        await query.edit_message_text("Nayi welcome image photo ke roop me bhejein.")
        return WAITING_SETTING

    setting_map = {
        "admin:set:whatsapp": ("whatsapp_link", "Naya WhatsApp link bhejein, jaise https://wa.me/91XXXXXXXXXX"),
        "admin:set:channel": ("channel_link", "Naya Telegram channel link bhejein."),
        "admin:set:upi": ("upi_id", "Naya UPI ID bhejein."),
        "admin:set:payment_name": ("payment_name", "Naya payment account/name bhejein."),
    }
    if data in setting_map:
        key, prompt = setting_map[data]
        context.user_data["admin_action"] = key
        await query.edit_message_text(prompt)
        return WAITING_SETTING

    if data.startswith("admin:list:"):
        status = data.split(":", 2)[2]
        apps = db.list_applications(None if status == "ALL" else status)
        if not apps:
            await query.edit_message_text("Koi application nahi mili.", reply_markup=admin_menu())
            return ConversationHandler.END
        await query.edit_message_text(
            f"ðŸ“‹ {len(apps)} applications mili. Details alag messages me bheji ja rahi hain.",
            reply_markup=admin_menu(),
        )
        for app in apps:
            caption = (
                f"<b>{html.escape(app['application_no'])}</b>\n"
                f"User: {html.escape(app['full_name'])}\n"
                f"Service: {html.escape(app['service_name'])}\n"
                f"Amount: â‚¹{app['amount']}\n"
                f"UTR: <code>{html.escape(app['utr'])}</code>\n"
                f"Status: {STATUS_LABELS.get(app['status'], app['status'])}"
            )
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=app["receipt_file_id"],
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=application_actions(app["application_no"]),
            )
        return ConversationHandler.END

    if data.startswith("admin:reject:"):
        app_no = data.split(":", 2)[2]
        context.user_data["admin_action"] = "reject"
        context.user_data["application_no"] = app_no
        await query.edit_message_caption(
            caption=(query.message.caption or "") + "\n\nReject reason text me bhejein."
        )
        return WAITING_REJECT_REASON

    if data.startswith("admin:status:"):
        _, _, app_no, status = data.split(":", 3)
        app = db.get_application(app_no)
        if not app:
            await query.answer("Application nahi mili.", show_alert=True)
            return ConversationHandler.END

        db.update_application_status(app_no, status)
        await _notify_user_status(context, app["user_id"], app_no, status, None)
        await query.answer("Status updated.", show_alert=True)
        new_caption = _replace_status_line(query.message.caption or "", status)
        await query.edit_message_caption(
            caption=new_caption,
            parse_mode=ParseMode.HTML,
            reply_markup=application_actions(app_no),
        )
        return ConversationHandler.END

    return ConversationHandler.END


def _replace_status_line(caption: str, status: str) -> str:
    lines = caption.splitlines()
    new_status = f"Status: {STATUS_LABELS.get(status, status)}"
    for i, line in enumerate(lines):
        if line.startswith("Status:"):
            lines[i] = new_status
            break
    else:
        lines.append(new_status)
    return "\n".join(lines)


async def receive_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update, context):
        return ConversationHandler.END

    db = _db(context)
    action = context.user_data.get("admin_action")

    if action in {"qr_file_id", "welcome_image_file_id"}:
        if not update.message.photo:
            await update.message.reply_text("Kripya photo bhejein.")
            return WAITING_SETTING
        db.set_setting(action, update.message.photo[-1].file_id)
        msg = "âœ… Payment QR successfully updated." if action == "qr_file_id" else "âœ… Welcome image successfully updated."
        await update.message.reply_text(msg, reply_markup=admin_menu())
    else:
        value = (update.message.text or "").strip()
        if not value:
            await update.message.reply_text("Value khaali nahi ho sakti.")
            return WAITING_SETTING
        if action in {"whatsapp_link", "channel_link"} and not value.startswith(("http://", "https://")):
            await update.message.reply_text("Valid link http:// ya https:// se shuru hona chahiye.")
            return WAITING_SETTING
        db.set_setting(action, value)
        await update.message.reply_text("âœ… Setting updated.", reply_markup=admin_menu())

    context.user_data.clear()
    return ConversationHandler.END


async def receive_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update, context):
        return ConversationHandler.END
    raw = (update.message.text or "").strip()
    if not raw.isdigit():
        await update.message.reply_text("Sirf number bhejein. Example: 1500")
        return WAITING_PRICE
    price = int(raw)
    if price < 0 or price > 100000:
        await update.message.reply_text("Price 0 se 100000 ke beech hona chahiye.")
        return WAITING_PRICE

    db = _db(context)
    code = context.user_data["service_code"]
    db.update_service_price(code, price)
    await update.message.reply_text(
        f"âœ… {context.user_data['service_name']} ka price â‚¹{price} set ho gaya.",
        reply_markup=admin_menu(),
    )
    context.user_data.clear()
    return ConversationHandler.END


async def receive_reject_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update, context):
        return ConversationHandler.END
    reason = (update.message.text or "").strip()
    if not reason:
        await update.message.reply_text("Reject reason khaali nahi ho sakta.")
        return WAITING_REJECT_REASON

    db = _db(context)
    app_no = context.user_data["application_no"]
    app = db.get_application(app_no)
    if not app:
        await update.message.reply_text("Application nahi mili.", reply_markup=admin_menu())
        context.user_data.clear()
        return ConversationHandler.END

    db.update_application_status(app_no, "REJECTED", reason)
    await _notify_user_status(context, app["user_id"], app_no, "REJECTED", reason)
    await update.message.reply_text("âŒ Application rejected aur user ko inform kar diya gaya.", reply_markup=admin_menu())
    context.user_data.clear()
    return ConversationHandler.END


async def _notify_user_status(context, user_id: int, app_no: str, status: str, note: str | None):
    text = (
        "ðŸ“¢ <b>Application Status Updated</b>\n\n"
        f"Application ID: <code>{html.escape(app_no)}</code>\n"
        f"Status: {STATUS_LABELS.get(status, status)}"
    )
    if note:
        text += f"\nReason/Note: {html.escape(note)}"
    try:
        await context.bot.send_message(chat_id=user_id, text=text, parse_mode=ParseMode.HTML)
    except Exception:
        pass
