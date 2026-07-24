from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from utils.constants import STATUS_LABELS


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("馃搵 Pending", callback_data="admin:list:PAYMENT_PENDING"),
                InlineKeyboardButton("馃搳 All", callback_data="admin:list:ALL"),
            ],
            [
                InlineKeyboardButton("馃挵 Change Prices", callback_data="admin:prices"),
                InlineKeyboardButton("馃柤 Change QR", callback_data="admin:set:qr"),
            ],
            [InlineKeyboardButton("馃寗 Welcome Image", callback_data="admin:set:welcome_image")],
            [InlineKeyboardButton("馃煝 Service Availability", callback_data="admin:availability")],
            [
                InlineKeyboardButton("馃敆 WhatsApp Link", callback_data="admin:set:whatsapp"),
                InlineKeyboardButton("馃摙 Channel Link", callback_data="admin:set:channel"),
            ],
            [
                InlineKeyboardButton("馃挸 UPI ID", callback_data="admin:set:upi"),
                InlineKeyboardButton("馃懁 Payment Name", callback_data="admin:set:payment_name"),
            ],
            [InlineKeyboardButton("馃搱 Statistics", callback_data="admin:stats")],
        ]
    )


def price_services_menu(services) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"{row['name']} 鈥� 鈧箋row['price']}", callback_data=f"admin:price:{row['code']}")]
        for row in services
    ]
    rows.append([InlineKeyboardButton("猬咃笍 Admin Home", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def application_actions(application_no: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("鉁� Approve Payment", callback_data=f"admin:status:{application_no}:PAYMENT_APPROVED"),
                InlineKeyboardButton("鉂� Reject", callback_data=f"admin:reject:{application_no}"),
            ],
            [
                InlineKeyboardButton("馃搫 Documents Pending", callback_data=f"admin:status:{application_no}:DOCUMENTS_PENDING"),
                InlineKeyboardButton("馃攧 Processing", callback_data=f"admin:status:{application_no}:PROCESSING"),
            ],
            [InlineKeyboardButton("馃帀 Mark Successful", callback_data=f"admin:status:{application_no}:SUCCESS")],
        ]
    )


def availability_services_menu(services) -> InlineKeyboardMarkup:
    rows = []
    for row in services:
        status = "鉁� Available" if row["active"] else "鉂� Not Available"
        rows.append([InlineKeyboardButton(
            f"{row['name']} 鈥� {status}",
            callback_data=f"admin:toggle:{row['code']}"
        )])
    rows.append([InlineKeyboardButton("猬咃笍 Admin Home", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)
