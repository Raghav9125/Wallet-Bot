from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from utils.constants import STATUS_LABELS


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📋 Pending", callback_data="admin:list:PAYMENT_PENDING"),
                InlineKeyboardButton("📊 All", callback_data="admin:list:ALL"),
            ],
            [
                InlineKeyboardButton("💰 Change Prices", callback_data="admin:prices"),
                InlineKeyboardButton("🖼 Change QR", callback_data="admin:set:qr"),
            ],
            [InlineKeyboardButton("🌄 Welcome Image", callback_data="admin:set:welcome_image")],
            [InlineKeyboardButton("🟢 Service Availability", callback_data="admin:availability")],
            [
                InlineKeyboardButton("🔗 WhatsApp Link", callback_data="admin:set:whatsapp"),
                InlineKeyboardButton("📢 Channel Link", callback_data="admin:set:channel"),
            ],
            [
                InlineKeyboardButton("💳 UPI ID", callback_data="admin:set:upi"),
                InlineKeyboardButton("👤 Payment Name", callback_data="admin:set:payment_name"),
            ],
            [InlineKeyboardButton("📈 Statistics", callback_data="admin:stats")],
        ]
    )


def price_services_menu(services) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"{row['name']} — ₹{row['price']}", callback_data=f"admin:price:{row['code']}")]
        for row in services
    ]
    rows.append([InlineKeyboardButton("⬅️ Admin Home", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def application_actions(application_no: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Approve Payment", callback_data=f"admin:status:{application_no}:PAYMENT_APPROVED"),
                InlineKeyboardButton("❌ Reject", callback_data=f"admin:reject:{application_no}"),
            ],
            [
                InlineKeyboardButton("📄 Documents Pending", callback_data=f"admin:status:{application_no}:DOCUMENTS_PENDING"),
                InlineKeyboardButton("🔄 Processing", callback_data=f"admin:status:{application_no}:PROCESSING"),
            ],
            [InlineKeyboardButton("🎉 Mark Successful", callback_data=f"admin:status:{application_no}:SUCCESS")],
        ]
    )


def availability_services_menu(services) -> InlineKeyboardMarkup:
    rows = []
    for row in services:
        status = "✅ Available" if row["active"] else "❌ Not Available"
        rows.append([InlineKeyboardButton(
            f"{row['name']} — {status}",
            callback_data=f"admin:toggle:{row['code']}"
        )])
    rows.append([InlineKeyboardButton("⬅️ Admin Home", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)
