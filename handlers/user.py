import html
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler
from database import Database
from keyboards.user_keyboards import main_menu, services_menu, understood_menu, whatsapp_button, support_contact_buttons, cancel_keyboard
from utils.constants import STATUS_LABELS
from utils.validators import is_valid_utr, normalize_utr

WAITING_FIRST_RECEIPT, WAITING_FIRST_UTR, WAITING_FINAL_RECEIPT, WAITING_FINAL_UTR = range(4)
GOOGLE_DOCS=['Mobile Number','Gmail ID','Aadhaar Card','PAN Card','Bank Account Details','IFSC Code']
COMMON_DOCS=['Mobile Number','Aadhaar Card','PAN Card','Bank Account Details','IFSC Code']

def _db(context): return context.application.bot_data['db']

async def _replace(update, context, text, reply_markup=None, parse_mode=None):
    q=update.callback_query
    if q and q.message:
        try: await q.delete_message()
        except Exception: pass
        await context.bot.send_message(q.message.chat_id,text,parse_mode=parse_mode,reply_markup=reply_markup)

async def _send_home(update, context, remove_callback_message=False):
    db=_db(context); channel=db.get_setting('channel_link','https://t.me/'); image=db.get_setting('welcome_image_file_id','')
    user=update.effective_user; first=html.escape(user.first_name if user else 'User')
    now=datetime.now(ZoneInfo('Asia/Kolkata')); date=now.strftime('%d %B %Y'); mins=now.hour*60+now.minute
    status='✅ <b>Service Available</b>' if 600 <= mins <= 1290 else '🌙 <b>Come Back Again Tomorrow at 10:00 AM</b>'
    text=(f'👋 <b>Hello {first}!</b>\n━━━━━━━━━━━━━━━━━━\n🎉 <b>India Business Wallets</b>\n\n'
          '💳 <b>Business Wallet Services</b>\n📝 Apply Now & Track Status\n\n'
          '🕙 <b>Working Hours</b>\n10:00 AM – 9:30 PM\n\n'
          f'{status}\n📅 <b>{date}</b>\n━━━━━━━━━━━━━━━━━━\nNeeche diye gaye button se service select karein 👇')
    if remove_callback_message and update.callback_query:
        try: await update.callback_query.delete_message()
        except Exception: pass
    if image:
        try:
            await context.bot.send_photo(update.effective_chat.id,image,caption=text,parse_mode=ParseMode.HTML,reply_markup=main_menu(channel)); return
        except Exception: pass
    await context.bot.send_message(update.effective_chat.id,text,parse_mode=ParseMode.HTML,reply_markup=main_menu(channel))

async def start(update, context): await _send_home(update,context,bool(update.callback_query))

async def callback_router(update, context):
    q=update.callback_query; await q.answer(); db=_db(context); data=q.data or ''
    if data=='user:home': await start(update,context); return
    if data=='user:apply':
        await _replace(update,context,'💼 <b>Aap kaunsa Business Wallet open karna chahte hain?</b>',services_menu(db.list_services(False)),ParseMode.HTML); return
    if data=='user:support':
        support_email = db.get_setting('support_email', 'support@example.com')
        support_text = (
            f"💬 <b>Support</b>\n\n"
            f"{html.escape(db.get_setting('support_text'))}\n\n"
            f"📧 <b>Email:</b> <code>{html.escape(support_email)}</code>"
        )
        await _replace(
            update,
            context,
            support_text,
            support_contact_buttons(
                db.get_setting('whatsapp_link'),
                support_email,
            ),
            ParseMode.HTML,
        )
        return
    if data=='user:status':
        apps=db.get_user_applications(q.from_user.id)
        if not apps: await _replace(update,context,'Aapki koi application nahi mili.',main_menu(db.get_setting('channel_link'))); return
        lines=['🔍 <b>Your Applications</b>\n']
        for a in apps:
            lines.append(f"<b>{html.escape(a['application_no'])}</b>\nService: {html.escape(a['service_name'])}\nTotal: ₹{a['amount']}\nFirst Paid: ₹{a['first_amount']}\nRemaining: ₹{a['remaining_amount']}\nStatus: {STATUS_LABELS.get(a['status'],a['status'])}\n")
        await _replace(update,context,'\n'.join(lines),main_menu(db.get_setting('channel_link')),ParseMode.HTML); return
    if data.startswith('svc:'):
        code=data.split(':',1)[1]; s=db.get_service(code)
        if not s: await _replace(update,context,'Service nahi mili.'); return
        if not s['active']:
            await _replace(update,context,f"❌ <b>{html.escape(s['name'])}</b> abhi available nahi hai.",whatsapp_button(db.get_setting('whatsapp_link')),ParseMode.HTML); return
        docs=GOOGLE_DOCS if code=='google_pay' else COMMON_DOCS; doc='\n'.join(f'• {html.escape(x)}' for x in docs)
        await _replace(update,context,f"💳 <b>{html.escape(s['name'])}</b>\n\n<b>Required Documents:</b>\n{doc}\n\n<b>Total Service Charge:</b> ₹{s['price']}\n\nPayment process samajhne ke baad continue karein.",understood_menu(code),ParseMode.HTML); return
    if data.startswith('understood:'):
        code=data.split(':',1)[1]; s=db.get_service(code,True)
        if not s: await _replace(update,context,'❌ Ye service abhi available nahi hai.'); return ConversationHandler.END
        first=s['price']//2; remaining=s['price']-first
        context.user_data.update(service_code=code,service_name=s['name'],amount=s['price'],first_amount=first,remaining_amount=remaining,payment_stage='first')
        qr=db.get_setting('first_payment_qr_file_id'); bank=html.escape(db.get_setting('first_payment_banking_name','India Business Wallet'))
        caption=(f"💳 <b>First Payment Required</b>\n\nTo start the application process, please pay 50% of the total service charge.\n\n"
                 f"Service: {html.escape(s['name'])}\nTotal Service Charge: ₹{s['price']}\nFirst Payment: ₹{first}\nRemaining Payment: ₹{remaining}\nBanking Name: <b>{bank}</b>\n\n"
                 "Please scan the QR code below and complete the first payment. After payment, upload the receipt screenshot.")
        try: await q.delete_message()
        except Exception: pass
        if qr: await context.bot.send_photo(q.message.chat_id,qr,caption=caption,parse_mode=ParseMode.HTML,reply_markup=cancel_keyboard())
        else: await context.bot.send_message(q.message.chat_id,caption+'\n\n⚠️ Admin has not set the First Payment QR yet.',parse_mode=ParseMode.HTML,reply_markup=cancel_keyboard())
        return WAITING_FIRST_RECEIPT
    if data.startswith('finalpay:'):
        app_no=data.split(':',1)[1]; app=db.get_application(app_no)
        if not app or app['user_id']!=q.from_user.id or app['status']!='FINAL_PAYMENT_REQUESTED': await q.answer('Final payment is not available.',show_alert=True); return ConversationHandler.END
        context.user_data.update(application_no=app_no,payment_stage='final')
        qr=db.get_setting(f"final_qr_{app['service_code']}"); bank=html.escape(db.get_setting(f"final_banking_name_{app['service_code']}",'India Business Wallet'))
        caption=(f"💳 <b>Final Payment Required</b>\n\nService: {html.escape(app['service_name'])}\nFinal Payment Due: ₹{app['remaining_amount']}\nBanking Name: <b>{bank}</b>\n\nPlease scan the QR code and upload the final payment receipt.")
        try: await q.delete_message()
        except Exception: pass
        if qr: await context.bot.send_photo(q.message.chat_id,qr,caption=caption,parse_mode=ParseMode.HTML,reply_markup=cancel_keyboard())
        else: await context.bot.send_message(q.message.chat_id,caption+'\n\n⚠️ Admin has not set the Final Payment QR yet.',parse_mode=ParseMode.HTML,reply_markup=cancel_keyboard())
        return WAITING_FINAL_RECEIPT
    if data=='user:cancel': context.user_data.clear(); await _replace(update,context,'Application process cancel kar diya gaya.',main_menu(db.get_setting('channel_link'))); return ConversationHandler.END

async def receive_first_receipt(update, context):
    if not update.message.photo: await update.message.reply_text('Please send the payment receipt as a photo.',reply_markup=cancel_keyboard()); return WAITING_FIRST_RECEIPT
    context.user_data['receipt_file_id']=update.message.photo[-1].file_id; await update.message.reply_text('✅ Receipt received. Now send the UTR/Transaction Reference Number.',reply_markup=cancel_keyboard()); return WAITING_FIRST_UTR

async def receive_first_utr(update, context):
    db=_db(context); raw=(update.message.text or '').strip()
    if not is_valid_utr(raw): await update.message.reply_text('Invalid UTR. Please send 6–30 letters/numbers.'); return WAITING_FIRST_UTR
    utr=normalize_utr(raw)
    if db.utr_exists(utr): await update.message.reply_text('❌ This UTR has already been submitted.'); return WAITING_FIRST_UTR
    req=('service_code','service_name','amount','receipt_file_id')
    if any(k not in context.user_data for k in req): context.user_data.clear(); await update.message.reply_text('Session expired. Send /start and try again.'); return ConversationHandler.END
    u=update.effective_user; app_no=db.create_application(user_id=u.id,full_name=u.full_name,username=u.username,service_code=context.user_data['service_code'],service_name=context.user_data['service_name'],amount=context.user_data['amount'],receipt_file_id=context.user_data['receipt_file_id'],utr=utr)
    app=db.get_application(app_no)
    whatsapp_message = (
        "Hello, I have submitted my first payment.\n\n"
        f"Application ID: {app_no}\n"
        f"Service: {app['service_name']}\n"
        f"Paid Amount: ₹{app['first_amount']}\n\n"
        "Please help me with the next process."
    )
    await update.message.reply_text(
        f"✅ <b>First Payment Submitted Successfully</b>\n\n"
        f"Application ID: <code>{app_no}</code>\n"
        f"Service: {html.escape(app['service_name'])}\n"
        f"Paid Amount: ₹{app['first_amount']}\n"
        f"Remaining Amount: ₹{app['remaining_amount']}\n"
        f"Status: {STATUS_LABELS['FIRST_PAYMENT_PENDING']}",
        parse_mode=ParseMode.HTML,
        reply_markup=whatsapp_button(
            db.get_setting('whatsapp_link'),
            whatsapp_message,
        ),
    )
    from keyboards.admin_keyboards import application_actions
    cap=(f"🆕 <b>New First Payment</b>\n\nApplication: <code>{app_no}</code>\nUser: {html.escape(u.full_name)}\nUser ID: <code>{u.id}</code>\nService: {html.escape(app['service_name'])}\nTotal: ₹{app['amount']}\nFirst Paid: ₹{app['first_amount']}\nUTR: <code>{utr}</code>\nStatus: {STATUS_LABELS['FIRST_PAYMENT_PENDING']}")
    for aid in context.application.bot_data['admin_ids']:
        try: await context.bot.send_photo(aid,app['first_receipt_file_id'],caption=cap,parse_mode=ParseMode.HTML,reply_markup=application_actions(app_no,app['status']))
        except Exception: pass
    context.user_data.clear(); return ConversationHandler.END

async def receive_final_receipt(update, context):
    if not update.message.photo: await update.message.reply_text('Please send the final payment receipt as a photo.',reply_markup=cancel_keyboard()); return WAITING_FINAL_RECEIPT
    context.user_data['final_receipt_file_id']=update.message.photo[-1].file_id; await update.message.reply_text('✅ Final receipt received. Now send the UTR number.',reply_markup=cancel_keyboard()); return WAITING_FINAL_UTR

async def receive_final_utr(update, context):
    db=_db(context); raw=(update.message.text or '').strip()
    if not is_valid_utr(raw): await update.message.reply_text('Invalid UTR.'); return WAITING_FINAL_UTR
    utr=normalize_utr(raw)
    if db.utr_exists(utr): await update.message.reply_text('❌ This UTR has already been submitted.'); return WAITING_FINAL_UTR
    app_no=context.user_data.get('application_no'); receipt=context.user_data.get('final_receipt_file_id'); app=db.get_application(app_no or '')
    if not app or not receipt: context.user_data.clear(); await update.message.reply_text('Session expired. Open your final payment notification again.'); return ConversationHandler.END
    db.submit_final_payment(app_no,receipt,utr); app=db.get_application(app_no)
    await update.message.reply_text(f"✅ <b>Final Payment Submitted</b>\n\nApplication ID: <code>{app_no}</code>\nFinal Payment: ₹{app['remaining_amount']}\nStatus: {STATUS_LABELS['FINAL_PAYMENT_PENDING']}",parse_mode=ParseMode.HTML)
    from keyboards.admin_keyboards import application_actions
    cap=(f"💳 <b>Final Payment Submitted</b>\n\nApplication: <code>{app_no}</code>\nUser: {html.escape(app['full_name'])}\nService: {html.escape(app['service_name'])}\nFinal Amount: ₹{app['remaining_amount']}\nUTR: <code>{utr}</code>\nStatus: {STATUS_LABELS['FINAL_PAYMENT_PENDING']}")
    for aid in context.application.bot_data['admin_ids']:
        try: await context.bot.send_photo(aid,receipt,caption=cap,parse_mode=ParseMode.HTML,reply_markup=application_actions(app_no,app['status']))
        except Exception: pass
    context.user_data.clear(); return ConversationHandler.END

async def cancel_text(update, context): context.user_data.clear(); await update.message.reply_text('Application cancelled.',reply_markup=main_menu(_db(context).get_setting('channel_link'))); return ConversationHandler.END
