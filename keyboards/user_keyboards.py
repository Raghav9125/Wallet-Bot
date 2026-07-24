from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu(channel_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('📝 Apply Now', callback_data='user:apply')],
        [InlineKeyboardButton('💬 Contact Support', callback_data='user:support')],
        [InlineKeyboardButton('📢 Join Official Channel', url=channel_link)],
        [InlineKeyboardButton('🔍 Check Application Status', callback_data='user:status')],
    ])

def services_menu(services) -> InlineKeyboardMarkup:
    rows=[]
    for row in services:
        status='✅ Available' if row['active'] else '❌ Not Available'
        rows.append([InlineKeyboardButton(f"{row['name']} — ₹{row['price']} — {status}", callback_data=f"svc:{row['code']}")])
    rows.append([InlineKeyboardButton('⬅️ Back', callback_data='user:home')])
    return InlineKeyboardMarkup(rows)

def understood_menu(code:str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('✅ Yes, I Understand', callback_data=f'understood:{code}')],
        [InlineKeyboardButton('❓ I Did Not Understand', callback_data='user:support')],
        [InlineKeyboardButton('⬅️ Back', callback_data='user:apply')],
    ])

def whatsapp_button(link:str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton('💬 Contact Directly on WhatsApp', url=link)]])

def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton('❌ Cancel', callback_data='user:cancel')]])

def final_payment_button(app_no:str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton('💳 Pay Final Amount', callback_data=f'finalpay:{app_no}')]])
