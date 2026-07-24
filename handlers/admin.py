import html
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler
from database import Database
from keyboards.admin_keyboards import admin_menu, application_actions, price_services_menu, availability_services_menu, payment_settings_menu, final_wallets_menu, final_wallet_setting_menu
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
    if data=='admin:home': await q.edit_message_text('🛠 <b>India Business Wallet Admin Panel</b>',parse_mode=ParseMode.HTML,reply_markup=admin_menu()); return ConversationHandler.END
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
    if data.startswith('admin:requestfinal:'):
        app_no=data.split(':',2)[2]; app=db.get_application(app_no)
        if not app: await q.answer('Application not found.',show_alert=True); return ConversationHandler.END
        qr=db.get_setting(f"final_qr_{app['service_code']}")
        if not qr: await q.answer('Set this wallet’s Final Payment QR first.',show_alert=True); return ConversationHandler.END
        db.request_final_payment(app_no); app=db.get_application(app_no)
        msg=(f"🎉 <b>Your Business Wallet Service Is Ready</b>\n\nApplication ID: <code>{app_no}</code>\nService: {html.escape(app['service_name'])}\n\nTotal Service Charge: ₹{app['amount']}\nFirst Payment Paid: ₹{app['first_amount']}\nFinal Payment Due: ₹{app['remaining_amount']}\n\nTap below to complete the final payment.")
        try: await context.bot.send_message(app['user_id'],msg,parse_mode=ParseMode.HTML,reply_markup=final_payment_button(app_no))
        except Exception: pass
        await q.answer('Final payment request sent.',show_alert=True); return ConversationHandler.END
    if data.startswith('admin:reject:'):
        context.user_data.update(admin_action='reject',application_no=data.split(':',2)[2]); await q.edit_message_caption(caption=(q.message.caption or '')+'\n\nSend rejection reason.'); return WAITING_REJECT
    if data.startswith('admin:status:'):
        _,_,app_no,status=data.split(':',3); app=db.get_application(app_no)
        if not app: await q.answer('Application not found.',show_alert=True); return ConversationHandler.END
        db.update_status(app_no,status); await notify_user(context,app['user_id'],app_no,status,None); await q.answer('Status updated.',show_alert=True)
        return ConversationHandler.END
    return ConversationHandler.END

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

async def notify_user(context,user_id,app_no,status,note):
    text=f"📢 <b>Application Status Updated</b>\n\nApplication ID: <code>{html.escape(app_no)}</code>\nStatus: {STATUS_LABELS.get(status,status)}"
    if note: text += f"\nReason: {html.escape(note)}"
    try: await context.bot.send_message(user_id,text,parse_mode=ParseMode.HTML)
    except Exception: pass
