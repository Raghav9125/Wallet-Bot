from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('📋 Pending', callback_data='admin:list:PENDING'), InlineKeyboardButton('📊 All', callback_data='admin:list:ALL')],
        [InlineKeyboardButton('💰 Change Prices', callback_data='admin:prices'), InlineKeyboardButton('🟢 Availability', callback_data='admin:availability')],
        [InlineKeyboardButton('🖼 Welcome Image', callback_data='admin:set:welcome_image')],
        [InlineKeyboardButton('💳 Payment Settings', callback_data='admin:payments')],
        [InlineKeyboardButton('🔗 WhatsApp Link', callback_data='admin:set:whatsapp'), InlineKeyboardButton('📢 Channel Link', callback_data='admin:set:channel')],
        [InlineKeyboardButton('📧 Support Email', callback_data='admin:set:support_email')],
        [InlineKeyboardButton('📈 Statistics', callback_data='admin:stats')],
    ])

def price_services_menu(services):
    rows=[[InlineKeyboardButton(f"{r['name']} — ₹{r['price']}", callback_data=f"admin:price:{r['code']}")] for r in services]
    rows.append([InlineKeyboardButton('⬅️ Admin Home', callback_data='admin:home')]); return InlineKeyboardMarkup(rows)

def availability_services_menu(services):
    rows=[]
    for r in services:
        s='✅ Available' if r['active'] else '❌ Not Available'
        rows.append([InlineKeyboardButton(f"{r['name']} — {s}", callback_data=f"admin:toggle:{r['code']}")])
    rows.append([InlineKeyboardButton('⬅️ Admin Home', callback_data='admin:home')]); return InlineKeyboardMarkup(rows)

def payment_settings_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('🖼 Common First Payment QR', callback_data='admin:set:first_qr')],
        [InlineKeyboardButton('🏦 First Payment Banking Name', callback_data='admin:set:first_bank')],
        [InlineKeyboardButton('📦 Final Payment QR Settings', callback_data='admin:final_wallets')],
        [InlineKeyboardButton('⬅️ Admin Home', callback_data='admin:home')],
    ])

def final_wallets_menu(services):
    rows=[[InlineKeyboardButton(r['name'], callback_data=f"admin:final:{r['code']}")] for r in services]
    rows.append([InlineKeyboardButton('⬅️ Payment Settings', callback_data='admin:payments')]); return InlineKeyboardMarkup(rows)

def final_wallet_setting_menu(code:str, name:str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('🖼 Change Final QR', callback_data=f'admin:set:final_qr:{code}')],
        [InlineKeyboardButton('🏦 Change Banking Name', callback_data=f'admin:set:final_bank:{code}')],
        [InlineKeyboardButton('⬅️ Wallet List', callback_data='admin:final_wallets')],
    ])

def application_actions(app_no: str, status: str):
    rows = []

    if status == 'FIRST_PAYMENT_PENDING':
        rows.append(
            [
                InlineKeyboardButton(
                    '✅ Approve First Payment',
                    callback_data=f'admin:status:{app_no}:FIRST_PAYMENT_APPROVED',
                ),
                InlineKeyboardButton(
                    '❌ Reject',
                    callback_data=f'admin:reject:{app_no}',
                ),
            ]
        )

    if status in {
        'FIRST_PAYMENT_APPROVED',
        'DOCUMENTS_PENDING',
        'PROCESSING',
    }:
        rows.append(
            [
                InlineKeyboardButton(
                    '📄 Documents Pending',
                    callback_data=f'admin:status:{app_no}:DOCUMENTS_PENDING',
                ),
                InlineKeyboardButton(
                    '🔄 Processing',
                    callback_data=f'admin:status:{app_no}:PROCESSING',
                ),
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    '🎉 Service Ready – Request Final Payment',
                    callback_data=f'admin:requestfinal:{app_no}',
                )
            ]
        )

    if status == 'FINAL_PAYMENT_PENDING':
        rows.append(
            [
                InlineKeyboardButton(
                    '✅ Approve Final Payment',
                    callback_data=f'admin:status:{app_no}:SUCCESS',
                ),
                InlineKeyboardButton(
                    '❌ Reject',
                    callback_data=f'admin:reject:{app_no}',
                ),
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                '🗑 Delete Permanently',
                callback_data=f'admin:deleteask:{app_no}',
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                '⬅️ Admin Home',
                callback_data='admin:home',
            )
        ]
    )
    return InlineKeyboardMarkup(rows)


def delete_confirmation_menu(app_no: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    '✅ Yes, Delete Permanently',
                    callback_data=f'admin:deleteconfirm:{app_no}',
                )
            ],
            [
                InlineKeyboardButton(
                    '❌ Cancel Delete',
                    callback_data=f'admin:deletecancel:{app_no}',
                )
            ],
        ]
    )
