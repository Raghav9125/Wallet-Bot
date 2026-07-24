from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu(channel_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📝 Apply Now", callback_data="user:apply")],
            [InlineKeyboardButton("💬 Contact Support", callback_data="user:support")],
            [InlineKeyboardButton("📢 Join Official Channel", url=channel_link)],
            [InlineKeyboardButton("🔍 Check Application Status", callback_data="user:status")],
        ]
    )


def services_menu(services) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"{row['name']} — ₹{row['price']}", callback_data=f"svc:{row['code']}")]
        for row in services
    ]
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="user:home")])
    return InlineKeyboardMarkup(rows)


def understood_menu(service_code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Yes, Main Samajh Gaya", callback_data=f"understood:{service_code}")],
            [InlineKeyboardButton("❓ Main Nahi Samjha", callback_data="user:support")],
            [InlineKeyboardButton("⬅️ Back", callback_data="user:apply")],
        ]
    )


def whatsapp_button(link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("💬 Contact Directly on WhatsApp", url=link)]]
    )


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Cancel", callback_data="user:cancel")]]
    )
