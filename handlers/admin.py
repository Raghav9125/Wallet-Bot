import html
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler
from database import Database
from keyboards.admin_keyboards import (
    admin_menu,
    application_actions,
    price_services_menu,
    availability_services_menu,
    payment_settings_menu,
    final_wallets_menu,
    final_wallet_setting_menu,
    delete_confirmation_menu,
)
from keyboards.user_keyboards import final_payment_button
from utils.constants import STATUS_LABELS

WAITING_SETTING, WAITING_PRICE, WAITING_REJECT = range(10,13)
def _db(context): return context.application.bot_data['db']
def _is_admin(update,context): return bool(update.effective_user and update.effective_user.id in context.application.bot_data['admin_ids'])

async def admin_command(update,context):
    if not _is_admin(update,context): await update.message.reply_text('⛔ Aap admin nahi hain.'); return
    await update.message.reply_text('🛠 <b>India Business Wallet Admin Panel</b>',parse_mode=ParseMode.HTML,reply_markup=admin_menu())

async def admin_callback(update,context):
    q=update.callback_query; await q.answer()
    if not _is_admin(update,context): await q.answer('Admin access required.',show_alert=True); return ConversationHandler.END
    db=_db(context); data=q.data or ''
    if data == 'admin:home':
        try:
            await q.delete_message()
        except Exception:
            pass
        await context.bot.send_message(
            chat_id=q.message.chat_id,
            text='🛠 <b>India Business Wallet Admin Panel</b>',
            parse_mode=ParseMode.HTML,
            reply_markup=admin_menu(),
        )
        return ConversationHandler.END
    if data=='admin:stats':
        s=db.stats(); await q.edit_message_text(f"📈 <b>Statistics</b>\n\nTotal: {s['total']}\nPending: {s['pending']}\nSuccessful: {s['success']}\nRejected: {s['rejected']}",parse_mode=ParseMode.HTML,reply_markup=admin_menu()); return ConversationHandler.END
    if data=='admin:prices': await q.edit_message_text('💰 Select service:',reply_markup=price_services_menu(db.list_services(False))); return ConversationHandler.END
    if data=='admin:availability': await q.edit_message_text('🟢 Tap a service to change status:',reply_markup=availability_services_menu(db.list_services(False))); return ConversationHandler.END
    if data.startswith('admin:toggle:'):
        code=data.split(':',2)[2]; s=db.get_service(code); db.set_service_active(code,not bool(s['active'])); await q.edit_message_text('🟢 Tap a service to change status:',reply_markup=availability_services_menu(db.list_services(False))); return ConversationHandler.END
    if data=='admin:payments': await q.edit_message_text('💳 <b>Payment Settings</b>',parse_mode=ParseMode.HTML,reply_markup=payment_settings_menu()); return ConversationHandler.END
    if data=='admin:final_wallets': await q.edit_message_text('Select wallet for Final Payment settings:',reply_markup=final_wallets_menu(db.list_services(False))); return ConversationHandler.END
    if data.startswith('admin:final:'):
        code=data.split(':',2)[2]; s=db.get_service(code); await q.edit_message_text(f"💳 <b>{html.escape(s['name'])} Final Payment</b>",parse_mode=ParseMode.HTML,reply_markup=final_wallet_setting_menu(code,s['name'])); return ConversationHandler.END
    if data.startswith('admin:price:'):
        code=data.split(':',2)[2]; s=db.get_service(code); context.user_data.update(admin_action='price',service_code=code,service_name=s['name']); await q.edit_message_text(f"Send new price for {s['name']} as a number."); return WAITING_PRICE
    photo_actions={'admin:set:welcome_image':'welcome_image_file_id','admin:set:first_qr':'first_payment_qr_file_id'}
    if data in photo_actions: context.user_data['admin_action']=photo_actions[data]; await q.edit_message_text('Send the new image as a Telegram photo.'); return WAITING_SETTING
    text_actions={
        'admin:set:whatsapp':'whatsapp_link',
        'admin:set:channel':'channel_link',
        'admin:set:support_email':'support_email',
        'admin:set:first_bank':'first_payment_banking_name',
    }
    if data in text_actions: context.user_data['admin_action']=text_actions[data]; await q.edit_message_text('Send the new value as text.'); return WAITING_SETTING
    if data.startswith('admin:set:final_qr:'):
        code=data.rsplit(':',1)[1]; context.user_data['admin_action']=f'final_qr_{code}'; await q.edit_message_text('Send this wallet’s new Final Payment QR as a photo.'); return WAITING_SETTING
    if data.startswith('admin:set:final_bank:'):
        code=data.rsplit(':',1)[1]; context.user_data['admin_action']=f'final_banking_name_{code}'; await q.edit_message_text('Send this wallet’s Final Payment Banking Name.'); return WAITING_SETTING
    if data.startswith('admin:list:'):
        status=data.split(':',2)[2]
        apps=db.list_applications(None if status=='ALL' else None)
        if status=='PENDING': apps=[a for a in apps if a['status'] in {'FIRST_PAYMENT_PENDING','FINAL_PAYMENT_PENDING'}]
        if not apps: await q.edit_message_text('No applications found.',reply_markup=admin_menu()); return ConversationHandler.END
        await q.edit_message_text(f'{len(apps)} applications found.',reply_markup=admin_menu())
        for a in apps:
            cap=(f"<b>{html.escape(a['application_no'])}</b>\nUser: {html.escape(a['full_name'])}\nService: {html.escape(a['service_name'])}\nTotal: ₹{a['amount']}\nFirst: ₹{a['first_amount']}\nRemaining: ₹{a['remaining_amount']}\nStatus: {STATUS_LABELS.get(a['status'],a['status'])}")
            photo=a['final_receipt_file_id'] if a['status']=='FINAL_PAYMENT_PENDING' and a['final_receipt_file_id'] else a['first_receipt_file_id'] or a['receipt_file_id']
            await context.bot.send_photo(q.message.chat_id,photo,caption=cap,parse_mode=ParseMode.HTML,reply_markup=application_actions(a['application_no'],a['status']))
        return ConversationHandler.END
    if data.startswith('admin:deleteask:'):
        app_no = data.split(':', 2)[2]
        app = db.get_application(app_no)
        if not app:
            await context.bot.send_message(
                q.message.chat_id,
                '❌ Application record nahi mila.',
            )
            return ConversationHandler.END

        warning = (
            '⚠️ <b>Permanent Delete Confirmation</b>\n\n'
            f'Application ID: <code>{html.escape(app_no)}</code>\n'
            f'Service: {html.escape(app["service_name"])}\n'
            f'User: {html.escape(app["full_name"])}\n\n'
            'Is record ko delete karne ke baad yah <b>All</b>, '
            '<b>Pending</b> aur user application history se hamesha ke liye '
            'hat jayega. Is action ko undo nahi kiya ja sakta.'
        )

        try:
            if q.message.photo:
                await q.edit_message_caption(
                    caption=warning,
                    parse_mode=ParseMode.HTML,
                    reply_markup=delete_confirmation_menu(app_no),
                )
            else:
                await q.edit_message_text(
                    warning,
                    parse_mode=ParseMode.HTML,
                    reply_markup=delete_confirmation_menu(app_no),
                )
        except Exception:
            await context.bot.send_message(
                q.message.chat_id,
                warning,
                parse_mode=ParseMode.HTML,
                reply_markup=delete_confirmation_menu(app_no),
            )
        return ConversationHandler.END

    if data.startswith('admin:deletecancel:'):
        app_no = data.split(':', 2)[2]
        app = db.get_application(app_no)
        if not app:
            await context.bot.send_message(
                q.message.chat_id,
                '❌ Application record nahi mila.',
            )
            return ConversationHandler.END

        caption = (
            f"<b>{html.escape(app['application_no'])}</b>\n"
            f"User: {html.escape(app['full_name'])}\n"
            f"Service: {html.escape(app['service_name'])}\n"
            f"Total: ₹{app['amount']}\n"
            f"First: ₹{app['first_amount']}\n"
            f"Remaining: ₹{app['remaining_amount']}\n"
            f"Status: {STATUS_LABELS.get(app['status'], app['status'])}"
        )

        try:
            if q.message.photo:
                await q.edit_message_caption(
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=application_actions(
                        app_no,
                        app['status'],
                    ),
                )
            else:
                await q.edit_message_text(
                    caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=application_actions(
                        app_no,
                        app['status'],
                    ),
                )
        except Exception:
            await context.bot.send_message(
                q.message.chat_id,
                '❎ Delete cancelled.',
                reply_markup=admin_menu(),
            )
        return ConversationHandler.END

    if data.startswith('admin:deleteconfirm:'):
        app_no = data.split(':', 2)[2]
        deleted = db.delete_application(app_no)

        if not deleted:
            await context.bot.send_message(
                q.message.chat_id,
                '❌ Application record nahi mila ya pehle hi delete ho chuka hai.',
                reply_markup=admin_menu(),
            )
            return ConversationHandler.END

        try:
            await q.delete_message()
        except Exception:
            pass

        await context.bot.send_message(
            q.message.chat_id,
            (
                '🗑 <b>Application Permanently Deleted</b>\n\n'
                f'Application ID: <code>{html.escape(app_no)}</code>\n\n'
                'Yah record ab All, Pending aur application history me '
                'dobara nahi dikhega.'
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=admin_menu(),
        )
        return ConversationHandler.END

    if data.startswith('admin:requestfinal:'):
        app_no = data.split(':', 2)[2]
        app = db.get_application(app_no)
        if not app:
            await context.bot.send_message(q.message.chat_id, '❌ Application not found.')
            return ConversationHandler.END

        qr = db.get_setting(f"final_qr_{app['service_code']}")
        if not qr:
            await context.bot.send_message(
                q.message.chat_id,
                '⚠️ Pehle is wallet ka Final Payment QR admin panel se set karein.'
            )
            return ConversationHandler.END

        db.request_final_payment(app_no)
        app = db.get_application(app_no)

        msg = (
            "🎉 <b>Your Business Wallet Service Is Ready</b>\n\n"
            f"Application ID: <code>{html.escape(app_no)}</code>\n"
            f"Service: {html.escape(app['service_name'])}\n\n"
            f"Total Service Charge: ₹{app['amount']}\n"
            f"First Payment Paid: ₹{app['first_amount']}\n"
            f"Final Payment Due: ₹{app['remaining_amount']}\n\n"
            "Tap below to complete the final payment."
        )

        try:
            await context.bot.send_message(
                app['user_id'],
                msg,
                parse_mode=ParseMode.HTML,
                reply_markup=final_payment_button(app_no),
            )
        except Exception as exc:
            await context.bot.send_message(
                q.message.chat_id,
                f"⚠️ Status update hua, lekin user ko notification nahi bhej paaya: {html.escape(str(exc))}",
                parse_mode=ParseMode.HTML,
            )

        new_caption = _updated_caption_status(
            q.message.caption or '',
            'FINAL_PAYMENT_REQUESTED',
        )
        try:
            await q.edit_message_caption(
                caption=new_caption,
                parse_mode=ParseMode.HTML,
                reply_markup=application_actions(app_no, 'FINAL_PAYMENT_REQUESTED'),
            )
        except Exception:
            await context.bot.send_message(
                q.message.chat_id,
                f"✅ Final payment request sent for {app_no}.",
            )
        return ConversationHandler.END
        db.request_final_payment(app_no); app=db.get_application(app_no)
        msg=(f"🎉 <b>Your Business Wallet Service Is Ready</b>\n\nApplication ID: <code>{app_no}</code>\nService: {html.escape(app['service_name'])}\n\nTotal Service Charge: ₹{app['amount']}\nFirst Payment Paid: ₹{app['first_amount']}\nFinal Payment Due: ₹{app['remaining_amount']}\n\nTap below to complete the final payment.")
        try: await context.bot.send_message(app['user_id'],msg,parse_mode=ParseMode.HTML,reply_markup=final_payment_button(app_no))
        except Exception: pass
        await q.answer('Final payment request sent.',show_alert=True); return ConversationHandler.END
    if data.startswith('admin:reject:'):
        context.user_data.update(admin_action='reject',application_no=data.split(':',2)[2]); await q.edit_message_caption(caption=(q.message.caption or '')+'\n\nSend rejection reason.'); return WAITING_REJECT
    if data.startswith('admin:status:'):
        _, _, app_no, status = data.split(':', 3)
        app = db.get_application(app_no)
        if not app:
            await context.bot.send_message(q.message.chat_id, '❌ Application not found.')
            return ConversationHandler.END

        db.update_status(app_no, status)
        await notify_user(context, app['user_id'], app_no, status, None)

        new_caption = _updated_caption_status(q.message.caption or '', status)
        try:
            await q.edit_message_caption(
                caption=new_caption,
                parse_mode=ParseMode.HTML,
                reply_markup=application_actions(app_no, status),
            )
        except Exception:
            await context.bot.send_message(
                q.message.chat_id,
                f"✅ {app_no} status updated: {STATUS_LABELS.get(status, status)}",
            )
        return ConversationHandler.END
    return ConversationHandler.END


def _updated_caption_status(caption: str, status: str) -> str:
    """Replace or append the Status line while preserving the admin card."""
    new_status = f"Status: {STATUS_LABELS.get(status, status)}"
    lines = caption.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("Status:"):
            lines[index] = new_status
            break
    else:
        lines.append(new_status)
    return "\n".join(lines)


async def receive_setting(update,context):
    if not _is_admin(update,context): return ConversationHandler.END
    db=_db(context); action=context.user_data.get('admin_action','')
    if action.endswith('_file_id') or action.startswith('final_qr_') or action=='first_payment_qr_file_id':
        if not update.message.photo: await update.message.reply_text('Please send a photo.'); return WAITING_SETTING
        db.set_setting(action,update.message.photo[-1].file_id)
    else:
        value=(update.message.text or '').strip()
        if not value: await update.message.reply_text('Value cannot be empty.'); return WAITING_SETTING
        if action in {'whatsapp_link','channel_link'} and not value.startswith(('http://','https://')):
            await update.message.reply_text('Link must start with http:// or https://')
            return WAITING_SETTING
        if action == 'support_email' and ('@' not in value or '.' not in value.split('@')[-1]):
            await update.message.reply_text('Please send a valid email address. Example: support@example.com')
            return WAITING_SETTING
        db.set_setting(action,value)
    context.user_data.clear(); await update.message.reply_text('✅ Setting updated.',reply_markup=admin_menu()); return ConversationHandler.END

async def receive_price(update,context):
    raw=(update.message.text or '').strip()
    if not raw.isdigit(): await update.message.reply_text('Send only a number.'); return WAITING_PRICE
    price=int(raw)
    if not 0 <= price <= 100000: await update.message.reply_text('Price must be between 0 and 100000.'); return WAITING_PRICE
    db=_db(context); db.update_service_price(context.user_data['service_code'],price); name=context.user_data['service_name']; context.user_data.clear(); await update.message.reply_text(f'✅ {name} price set to ₹{price}.',reply_markup=admin_menu()); return ConversationHandler.END

async def receive_reject(update,context):
    reason=(update.message.text or '').strip()
    if not reason: await update.message.reply_text('Reason cannot be empty.'); return WAITING_REJECT
    db=_db(context); app_no=context.user_data['application_no']; app=db.get_application(app_no)
    if app: db.update_status(app_no,'REJECTED',reason); await notify_user(context,app['user_id'],app_no,'REJECTED',reason)
    context.user_data.clear(); await update.message.reply_text('❌ Rejected and user notified.',reply_markup=admin_menu()); return ConversationHandler.END

async def notify_user(context, user_id, app_no, status, note):
    if status == 'SUCCESS':
        text = (
            "🎉 <b>Your Service Has Been Completed Successfully!</b>\n\n"
            f"Application ID: <code>{html.escape(app_no)}</code>\n"
            "Status: ✅ Service Successfully Completed\n\n"
            "Thank you for choosing <b>India Business Wallets</b>.\n"
            "We truly appreciate your trust in our service.\n\n"
            "🌟 Have a wonderful and successful day!"
        )
    else:
        text = (
            "📢 <b>Application Status Updated</b>\n\n"
            f"Application ID: <code>{html.escape(app_no)}</code>\n"
            f"Status: {STATUS_LABELS.get(status, status)}"
        )
        if note:
            text += f"\nReason: {html.escape(note)}"

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass
