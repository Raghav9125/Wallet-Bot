from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu(channel_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("馃摑 Apply Now", callback_data="user:apply")],
            [InlineKeyboardButton("馃挰 Contact Support", callback_data="user:support")],
            [InlineKeyboardButton("馃摙 Join Official Channel", url=channel_link)],
            [InlineKeyboardButton("馃攳 Check Application Status", callback_data="user:status")],
        ]
    )


def services_menu(services) -> InlineKeyboardMarkup:
    rows = []
    for row in services:
        status = "鉁� Available" if row["active"] else "鉂� Not Available"
        rows.append([InlineKeyboardButton(
            f"{row['name']} 鈥� 鈧箋row['price']} 鈥� {status}",
            callback_data=f"svc:{row['code']}"
        )])
    rows.append([InlineKeyboardButton("猬咃笍 Back", callback_data="user:home")])
    return InlineKeyboardMarkup(rows)


def understood_menu(service_code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("鉁� Yes, Main Samajh Gaya", callback_data=f"understood:{service_code}")],
            [InlineKeyboardButton("鉂� Main Nahi Samjha", callback_data="user:support")],
            [InlineKeyboardButton("猬咃笍 Back", callback_data="user:apply")],
        ]
    )


def whatsapp_button(link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("馃挰 Contact Directly on WhatsApp", url=link)]]
    )


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("鉂� Cancel", callback_data="user:cancel")]]
    )
