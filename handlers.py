import io
import re
import base64
import logging
from typing import Optional, Any
import datetime
import time  # 🔥 এই লাইনটা নতুন অ্যাড করা হলো
from aiogram.types import Message, CallbackQuery
from aiogram import F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from panel_manager import panel_router, SecurePanelFSM, ApiPanelFSM
from aiogram.filters import StateFilter

# 🔥 বট স্টার্ট হওয়ার বর্তমান সময় রেকর্ড করে রাখা হলো (এর আগের কোনো ডেটা আর ধরবে না)
BOT_START_TIME = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
import aiosqlite

from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CopyTextButton,
)
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from config import (
    BOT_TOKEN,
    OTP_GROUP_LINK,
    UPDATE_CHANNEL_LINK,
    EXTRA_LINK_1,
    EXTRA_LINK_2, 
    BTN_EMOJIS,
    format_p_emo,
    DB_PATH,
    OTP_GROUP_ID,
    SYS_EMOJI,
)
from database import (
    db_mgr,
    GLOBAL_COUNTRY_MAP,
    resolve_universal_country,
)

# 🔥 অ্যাডমিন নোটিশের স্টেট ক্লাসটা ঠিক এইখানে বসে গেলো
class AdminNoticeState(StatesGroup):
    waiting_for_message = State()
    target_user_id = State()
# =========================================================
# LOGGER
# =========================================================

logger = logging.getLogger(__name__)

router = Router()
router.include_router(panel_router)  # 🔥 Ei line ta add korbe

# 🔥 ঠিক এইখানে গ্লোবাল ব্যান মিডলওয়্যার এবং নোটিশ হ্যান্ডলার বসিয়ে দিন:

from aiogram import BaseMiddleware

class GlobalBanMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = event.from_user
        if not user:
            return await handler(event, data)
            
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user.id,))
            row = await cursor.fetchone()
            is_banned = 0
            if row:
                try:
                    is_banned = row["is_banned"]
                except Exception:
                    is_banned = 0
            
        if is_banned:
            # শুধু Support এবং Unban/Notice বাটন কাজ করবে
            if isinstance(event, types.CallbackQuery):
                if "support" in event.data.lower() or "sys_" in event.data:
                    return await handler(event, data)
                await event.answer("🚫 You are permanently BANNED! Only Support is allowed.", show_alert=True)
                return
            elif isinstance(event, types.Message):
                if event.text and "/start" in event.text:
                    pass # Start অ্যালাউ করা হলো যাতে সাপোর্ট বাটন দেখতে পায়
                else:
                    await event.answer("🚫 You are permanently BANNED from using this bot. Contact Support.")
                    return
                    
        return await handler(event, data)

# 🔥 গ্লোবাল লক চালু
router.message.middleware(GlobalBanMiddleware())
router.callback_query.middleware(GlobalBanMiddleware())

# 🔥 Notice Handler একদম ওপরে রাখা হলো যাতে অন্য কেউ ক্যাচ না করে
@router.message(AdminNoticeState.waiting_for_message)
async def process_sys_notice_send(message: types.Message, state: FSMContext):
    if message.text and message.text.lower() == "/cancel":
        await state.clear()
        return await message.reply("Action cancelled.")
        
    data = await state.get_data()
    target_id = data.get("target_user_id")
    
    notice_text = (
        f'<tg-emoji emoji-id="5420323339723881652">⚠️</tg-emoji> <b>Message from Admin:</b>\n\n'
        f'{message.html_text}'
    )
    
    try:
        await message.bot.send_message(chat_id=target_id, text=notice_text)
        await message.reply(f"✅ Notice sent successfully to user {target_id}.")
    except Exception:
        await message.reply("❌ Failed to send notice. User might have blocked the bot.")
        
    await state.clear()

# =========================================================
# CONSTANTS
# =========================================================

MENU_GET = "𝐆𝐄𝐓 𝐍𝐔𝐌𝐁𝐄𝐑"
MENU_STATUS = "𝐒𝐓𝐀𝐓𝐔𝐒"
MENU_ACTIVE = "𝐀𝐂𝐓𝐈𝐕𝐄 𝐍𝐔𝐌𝐁𝐄𝐑"
MENU_SUPPORT = "𝐒𝐔𝐏𝐏𝐎𝐑𝐓"
MENU_REFER = "𝐑𝐄𝐅𝐄𝐑"
MENU_WALLET = "𝐖𝐀𝐋𝐋𝐄𝐓"
MENU_ADMIN = "𝐀𝐃𝐌𝐈𝐍 𝐏𝐀𝐍𝐄𝐋"
MENU_LEADERBOARD = "𝐋𝐄𝐀𝐃𝐄𝐑𝐁𝐎𝐀𝐑𝐃"
# =========================================================
# PREMIUM / CUSTOM EMOJI IDs
# =========================================================

SERVICE_EMOJIS = {
    "facebook": {"emoji_id": "5323261730283863478", "placeholder": ""},
    "tiktok": {"emoji_id": "5327982530702359565", "placeholder": ""},
    "whatsapp": {"emoji_id": "5334998226636390258", "placeholder": ""},
    "telegram": {"emoji_id": "5244763347454300958", "placeholder": ""},
    "instagram": {"emoji_id": "5319160079465857105", "placeholder": ""},
    "paypal": {"emoji_id": "5364111181415996352", "placeholder": ""},
    "discord": {"emoji_id": "5325612636467903082", "placeholder": ""},
    "amazon": {"emoji_id": "6161414526399948623", "placeholder": ""},
    "pariland": {"emoji_id": "6161016606269907350", "placeholder": ""},
    "uber": {"emoji_id": "5298715455316303708", "placeholder": ""},
    "shopee": {"emoji_id": "6161414526399948623", "placeholder": ""},
    "apple": {"emoji_id": "5334955749409834455", "placeholder": ""},
    "hsbc": {"emoji_id": "6249045530119249807", "placeholder": ""},
    "alfursan": {"emoji_id": "6156449849148448697", "placeholder": ""},
    "microsoft": {"emoji_id": "5370857634440170316", "placeholder": ""},
    "bolt": {"emoji_id": "6179401140765992368", "placeholder": ""},
    "binance": {"emoji_id": "5281029063459234079", "placeholder": ""},
    "infosms": {"emoji_id": "5796690095511703420", "placeholder": ""},
    "signal": {"emoji_id": "5328050550099427291", "placeholder": ""},
    "imo": {"emoji_id": "6219680125751926660", "placeholder": ""},
    "indrive": {"emoji_id": "6163492921204024370", "placeholder": ""},
    "fib": {"emoji_id": "5332455502917949981", "placeholder": ""},
    "default": {"emoji_id": "5346066456142429527", "placeholder": ""},
}

def format_p_emo(emoji_id: str, fallback: str) -> str:
    if emoji_id and emoji_id != "0": 
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    return fallback

def get_service_custom_emoji_id(service_name: str) -> str:
    lower_s = str(service_name).lower().strip()
    # 🔥 Since it's a dictionary now, we need to extract ["emoji_id"]
    service_data = SERVICE_EMOJIS.get(lower_s, SERVICE_EMOJIS["default"])
    return service_data["emoji_id"]


COUNTRY_EMOJIS = {
    "AFGHANISTAN": "5294096544406976986",
    "ALBANIA": "5294250613473820536",
    "ALGERIA": "5294286064133879533",
    "ANDORRA": "5292244112127309992",
    "ANGOLA": "5292213828312905338",
    "ANTIGUA AND BARBUDA": "5292270732334611090",
    "ARGENTINA": "5294179501700298684",
    "ARMENIA": "5291774508993100789",
    "AUSTRALIA": "5293988654828502400",
    "AUSTRIA": "5292285751835244257",
    "AZERBAIJAN": "5292095441834359120",
    "BAHAMAS": "5294068987896806041",
    "BAHRAIN": "5294282555145598445",
    "BANGLADESH": "5294500851153385168",
    "BARBADOS": "5294290943216727979",
    "BELARUS": "5294128460308952497",
    "BELGIUM": "5294255703010064221",
    "BELIZE": "5294192678659969543",
    "BENIN": "5294279724762151165",
    "BERMUDA": "5292231854290647654",
    "BHUTAN": "5294257004385155104",
    "BOLIVIA": "5294033743395176282",
    "BOSNIA AND HERZEGOVINA": "5294316730200375501",
    "BOTSWANA": "5291869986116090404",
    "BRAZIL": "5294401014638590651",
    "BRUNEI": "5292093668012865550",
    "BULGARIA": "5294009549844398897",
    "BURKINA FASO": "5292036948674754260",
    "BURUNDI": "5292178265983695853",
    "CABO VERDE": "5294466272371686676",
    "CAMBODIA": "5294018354527353443",
    "CAMEROON": "5294089569380088333",
    "CANADA": "5292023956398684554",
    "CENTRAL AFRICAN REPUBLIC": "5294120372885536804",
    "CHAD": "5291961301415772318",
    "CHILE": "5291837722321762793",
    "CHINA": "5294528665361594977",
    "COLOMBIA": "5294323009442559993",
    "COMOROS": "5294064022914611434",
    "CONGO": "5292182775699355868",
    "COSTA RICA": "5294360221039211867",
    "CROATIA": "5294379818974983811",
    "CYPRUS": "5292256812345604723",
    "CZECH REPUBLIC": "5294420372056194185",
    "DENMARK": "5294524868610505865",
    "DJIBOUTI": "5291791985215026199",
    "DOMINICA": "5292080314959543164",
    "DOMINICAN REPUBLIC": "5291962040150145704",
    "DR CONGO": "5294524718286648684",
    "ECUADOR": "5294034005388180164",
    "EGYPT": "5292168898660021541",
    "EL SALVADOR": "5291933873754616525",
    "ENGLAND": "5294044768576225045",
    "EQUATORIAL GUINEA": "5294232686280325366",
    "ESTONIA": "5294406580916207129",
    "ESWATINI": "5292027955013238582",
    "ETHIOPIA": "5294512168392209285",
    "EUROPEAN UNION": "5292215219882326573",
    "FIJI": "5294307040754157008",
    "FINLAND": "5292088630016227941",
    "FRANCE": "5294324697364707139",
    "GABON": "5294404137079813976",
    "GAMBIA": "5292179193696630126",
    "GEORGIA": "5292010100834186995",
    "GERMANY": "5294470636058458270",
    "GHANA": "5294208810557126145",
    "GREECE": "5292126163735427226",
    "GRENADA": "5291955851102271781",
    "GUATEMALA": "5294371392249149894",
    "GUINEA": "5294318061640235074",
    "GUINEA-BISSAU": "5292022620663855264",
    "GUYANA": "5294398167075273417",
    "HAITI": "5294173759329025494",
    "HONDURAS": "5292122826545838570",
    "HUNGARY": "5291889682836109921",
    "ICELAND": "5291879185936037620",
    "INDIA": "5294510171232419362",
    "INDONESIA": "5294364674920301441",
    "IRAN": "5294418473680649993",
    "IRAQ": "5294084990944952018",
    "IRELAND": "5294046293289614882",
    "ISRAEL": "5291780457522806625",
    "ITALY": "5291783691633179315",
    "JAMAICA": "5294171766464198371",
    "JAPAN": "5292252637637394017",
    "JORDAN": "5294235112936847701",
    "KAZAKHSTAN": "5292132601891406351",
    "KENYA": "5293996922640546414",
    "KIRIBATI": "5294082864936140082",
    "KOSOVO": "5294020669514727367",
    "KUWAIT": "5294510665153657908",
    "KYRGYZSTAN": "5294072870547241138",
    "LAOS": "5294515754689902278",
    "LATVIA": "5294197897045228028",
    "LEBANON": "5291982140597091240",
    "LESOTHO": "5294143643018345113",
    "LIBERIA": "5292232056154109362",
    "LIBYA": "5294081679525165705",
    "LIECHTENSTEIN": "5291983553641331042",
    "LITHUANIA": "5294343436307020064",
    "LUXEMBOURG": "5294194808963743125",
    "MADAGASCAR": "5291743636768176974",
    "MALAYSIA": "5292109885809376609",
    "MALDIVES": "5292156288636041561",
    "MALI": "5292134435842439385",
    "MALTA": "5294538900268661088",
    "MARSHALL ISLANDS": "5292053029032311205",
    "MARTINIQUE": "5292100419701455839",
    "MAURITIUS": "5294442087410842048",
    "MEXICO": "5291875964710567607",
    "MICRONESIA": "5292212260649843267",
    "MOLDOVA": "5292243875904108185",
    "MONACO": "5291754241042429367",
    "MONGOLIA": "5294157674676500911",
    "MONTENEGRO": "5294007037288527822",
    "MOROCCO": "5294475854443723073",
    "MOZAMBIQUE": "5291747167231294255",
    "NAMIBIA": "5291794609440047824",
    "NEPAL": "5294374235517500613",
    "NETHERLANDS": "5294241847445566691",
    "NEW ZEALAND": "5292140092314367840",
    "NIGER": "5294512361665738891",
    "NIGERIA": "5294130362979465506",
    "NORTH MACEDONIA": "5294302797326465547",
    "NORWAY": "5291807953903434152",
    "OMAN": "5291911668773699198",
    "PAKISTAN": "5291913455480092451",
    "PALAU": "5294108389926780755",
    "PALESTINE": "5294319208396502996",
    "PANAMA": "5291750233837944755",
    "PAPUA NEW GUINEA": "5294033584481383769",
    "PARAGUAY": "5291897044410055523",
    "PERU": "5291960111709830256",
    "PHILIPPINES": "5294212306660507275",
    "PORTUGAL": "5292106978116516589",
    "PUERTO RICO": "5294287021911586554",
    "QATAR": "5294044214525442531",
    "ROMANIA": "5294080455459486227",
    "RUSSIA": "5291734595862018096",
    "RWANDA": "5294524765531291089",
    "SAINT KITTS AND NEVIS": "5291931442803126844",
    "SAINT LUCIA": "5294255234858630622",
    "SAINT VINCENT AND THE GRENADINES": "5294418671249142859",
    "SAMOA": "5294254500419221878",
    "SAN MARINO": "5292127714218622101",
    "SAO TOME AND PRINCIPE": "5294491312031021064",
    "SAUDI ARABIA": "5294345751294393183",
    "SCOTLAND": "5292267541173909411",
    "SENEGAL": "5292266553331433530",
    "SERBIA": "5291929449938302792",
    "SEYCHELLES": "5294299185258969386",
    "SIERRA LEONE": "5292063143680291937",
    "SINGAPORE": "5294406215843985891",
    "SLOVAKIA": "5292028285725719287",
    "SLOVENIA": "5294068021529164085",
    "SOLOMON ISLANDS": "5292246096402201145",
    "SOMALIA": "5294078355220478091",
    "SOUTH AFRICA": "5294100525841659817",
    "SOUTH KOREA": "5294103841556413525",
    "SOUTH SUDAN": "5292027637185658003",
    "SPAIN": "5294323318680206912",
    "SRI LANKA": "5291887612661872281",
    "SUDAN": "5294204670208653563",
    "SURINAME": "5294004254149721569",
    "SWEDEN": "5292195991313726356",
    "SWITZERLAND": "5291752789343485768",
    "TAJIKISTAN": "5292058496525679262",
    "TANZANIA": "5292124531647854609",
    "THAILAND": "5294308565467543746",
    "TIMOR-LESTE": "5292026151126970843",
    "TOGO": "5294043261042703048",
    "TRINIDAD AND TOBAGO": "5294412254568004481",
    "TUNISIA": "5294039313967757294",
    "TURKMENISTAN": "5292055356904585500",
    "TURKEY": "5292218402453075461",
    "UAE": "5294285256680029509",
    "UGANDA": "5294079660890535793",
    "UNITED KINDOM": "5294447773947543583",
    "UKRAINE": "5294210833486724321",
    "URUGUAY": "5291863865787694128",
    "USA": "5291747893080766866",
    "UZBEKISTAN": "5294289324014057127",
    "MAURITANIA": "5404566049607663230",
    "VATICAN CITY": "5294429004940458392",
    "VIETNAM": "5294317155402137202",
    "VIRGIN ISLANDS": "5294211696775150914",
    "SYRIA": "5291969728141625850",
    "YEMEN": "5291806802852198444",
    "ZAMBIA": "5294161127830205421",
    "ZIMBABWE": "5292167442666110763",
}

# =========================================================
# BUTTON EMOJI IDs
# =========================================================

E_GET = "5800835941543186089"
E_STATUS = "5258028182149286660"
E_ACTIVE = "5386367538735104399"
E_SUPPORT = "5366043289633962337"
E_REFER = "5332724926216428039"
E_WALLET = "5215420556089776398"
E_ADMIN = "5316832430529722441"
E_BACK = "6206505206197261313"
E_VERIFY = "5330194932781050507"
E_GROUP = "5841494459904168607"
E_CHANGE = "5370715282044100355"
E_CC = "5188540541922480562"


# =========================================================
# FSM
# =========================================================

class Form(StatesGroup):
    waiting_for_numbers = State()
    waiting_for_service = State()
    waiting_for_nums_per_user = State()
    waiting_for_rate = State()

    waiting_for_broadcast_decision = State()
    waiting_for_broadcast_msg = State()

    waiting_for_withdraw_amt = State()
    waiting_for_withdraw_number = State()

    waiting_for_set_wallet_number = State()

    waiting_for_new_admin = State()
    waiting_for_edit_support = State()
    waiting_for_edit_min_with = State()

    waiting_for_req_channel = State()
    waiting_for_new_service = State()

    waiting_for_edit_service_rate = State()
    # Eita notun add koro
    waiting_for_panel_url = State()
    editing_panel_name = State()

# =========================================================
# BOLD FONT
# =========================================================

def to_bold_font(text: str) -> str:
    normal = (
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
    )

    bold = (
        "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇"
        "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭"
        "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
    )

    return text.translate(str.maketrans(normal, bold))


# =========================================================
# UNICODE BOLD -> NORMAL
# =========================================================

_BOLD_NORMAL = (
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
)

_BOLD_CHARS = (
    "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇"
    "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭"
    "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
)

BOLD_TO_NORMAL = str.maketrans(
    _BOLD_CHARS,
    _BOLD_NORMAL,
)


def normalize_button_text(text: str) -> str:
    if not text:
        return ""

    text = text.translate(BOLD_TO_NORMAL)

    text = (
        text.replace("\u200b", "")
        .replace("\u200c", "")
        .replace("\u200d", "")
        .replace("\ufeff", "")
    )

    text = re.sub(r"\s+", " ", text).strip()

    return text.upper()


# =========================================================
# CALLBACK DATA PACK / UNPACK
# =========================================================

def pack_callback(prefix: str, *values: Any) -> str:
    raw = "||".join(str(v) for v in values)

    encoded = base64.urlsafe_b64encode(
        raw.encode("utf-8")
    ).decode("ascii").rstrip("=")

    return f"{prefix}:{encoded}"


def unpack_callback(data: str, prefix: str) -> list[str]:
    marker = f"{prefix}:"

    if not data.startswith(marker):
        return []

    encoded = data[len(marker):]

    padding = "=" * (-len(encoded) % 4)

    try:
        raw = base64.urlsafe_b64decode(
            encoded + padding
        ).decode("utf-8")
    except Exception:
        return []

    return raw.split("||")


# =========================================================
# SERVICE EMOJI
# =========================================================

def get_service_custom_emoji_id(service_name: str) -> str:
    name = str(service_name).lower().strip()

    return SERVICE_EMOJIS.get(
        name,
        SERVICE_EMOJIS["default"],
    )["emoji_id"]


def get_service_placeholder(service_name: str) -> str:
    name = str(service_name).lower().strip()

    return SERVICE_EMOJIS.get(
        name,
        SERVICE_EMOJIS["default"],
    )["placeholder"]


# =========================================================
# COUNTRY EMOJI
# =========================================================

def get_country_custom_emoji_id(country_name: str) -> str:
    base_country = re.sub(r'\s*\d+$', '', str(country_name)).strip().upper()
    
    for key, emoji_id in COUNTRY_EMOJIS.items():
        if key != "default" and key in base_country:
            return emoji_id
    return COUNTRY_EMOJIS["default"]


# =========================================================
# PHONE NUMBER
# =========================================================

def extract_pure_number_without_cc(
    phone: str,
    country: str,
) -> str:

    clean = re.sub(r"\D", "", str(phone))
    base_country = re.sub(r'\s*\d+$', '', str(country)).strip().upper()

    for prefix in sorted(
        GLOBAL_COUNTRY_MAP.keys(),
        key=len,
        reverse=True,
    ):
        try:
            mapped_country = str(GLOBAL_COUNTRY_MAP[prefix]).strip().upper()

            if (
                mapped_country == base_country
                and clean.startswith(str(prefix))
            ):
                return clean[len(str(prefix)):]

        except Exception:
            continue

    return clean


# =========================================================
# SAFE BOT HELPERS
# =========================================================

async def send_msg(
    bot,
    chat_id: int | str,
    text: str,
    reply_markup=None,
):
    try:
        return await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )

    except TelegramForbiddenError:
        logger.warning(
            "Bot blocked by user/chat %s",
            chat_id,
        )
        return None

    except Exception:
        logger.exception(
            "send_message failed for %s",
            chat_id,
        )
        return None


async def safe_edit(
    message: types.Message,
    text: str,
    reply_markup=None,
):
    try:
        return await message.edit_text(
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )

    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return message

        logger.warning(
            "edit_text TelegramBadRequest: %s",
            exc,
        )

    except Exception:
        logger.exception("safe_edit failed")

    return None


async def safe_answer(
    callback: types.CallbackQuery,
    text: str = "",
    show_alert: bool = False,
):
    try:
        await callback.answer(
            text=text,
            show_alert=show_alert,
        )
    except Exception:
        pass


# =========================================================
# MAIN REPLY KEYBOARD
# =========================================================

def main_permanent_keyboard(
    user_id: int,
    is_admin: bool = False,
) -> ReplyKeyboardMarkup:

    rows = [
        [
            KeyboardButton(text="𝐆𝐄𝐓 𝐍𝐔𝐌𝐁𝐄𝐑", style="success", icon_custom_emoji_id=E_GET),
            KeyboardButton(text="𝐒𝐓𝐀𝐓𝐔𝐒", style="primary", icon_custom_emoji_id=E_STATUS),
        ],
        [
            KeyboardButton(text="𝐀𝐂𝐓𝐈𝐕𝐄 𝐍𝐔𝐌𝐁𝐄𝐑", style="primary", icon_custom_emoji_id=E_ACTIVE),
            KeyboardButton(text="𝐒𝐔𝐏𝐏𝐎𝐑𝐓", style="primary", icon_custom_emoji_id=E_SUPPORT),
        ],
        [
            KeyboardButton(text="𝐑𝐄𝐅𝐄𝐑", style="primary", icon_custom_emoji_id=E_REFER),
            KeyboardButton(text="𝐖𝐀𝐋𝐋𝐄𝐓", style="success", icon_custom_emoji_id=E_WALLET),
        ],
        [
            KeyboardButton(text="𝐋𝐄𝐀𝐃𝐄𝐑𝐁𝐎𝐀𝐑𝐃", style="primary", icon_custom_emoji_id="6307633028680130361"),
        ]
    ]

    if is_admin:
        rows.append([KeyboardButton(text="𝐀𝐃𝐌𝐈𝐍 𝐏𝐀𝐍𝐄𝐋", style="danger", icon_custom_emoji_id=E_ADMIN)])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Choose an option...",
    )


# =========================================================
# INLINE BUTTON HELPER
# =========================================================

def ib(
    text: str,
    *,
    callback_data: Optional[str] = None,
    url: Optional[str] = None,
    style: Optional[str] = None,
    emoji_id: Optional[str] = None,
    copy_text: Optional[str] = None,
):
    kwargs = {
        "text": text,
    }

    if callback_data is not None:
        kwargs["callback_data"] = callback_data

    if url is not None:
        kwargs["url"] = url

    if style is not None:
        kwargs["style"] = style

    if emoji_id is not None:
        kwargs["icon_custom_emoji_id"] = emoji_id

    if copy_text is not None:
        kwargs["copy_text"] = CopyTextButton(
            text=copy_text
        )

    return InlineKeyboardButton(**kwargs)


# =========================================================
# ADMIN PANEL
# =========================================================

def admin_inline_panel() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                ib(
                    "🔌 API Panels",
                    callback_data="adm:panels",
                    style="primary",
                    emoji_id="5316832430529722441",
                ),
                ib(
                    " Inventory Dashboard",
                    callback_data="adm:inventory",
                    style="primary",
                    emoji_id=E_STATUS,
                ),
            ],
            [
                ib(
                    " Add Numbers Pool",
                    callback_data="adm:addnum",
                    style="success",
                    emoji_id=E_GET,
                ),
                ib(
                    " Add Service",
                    callback_data="adm:addservice",
                    style="success",
                    emoji_id=E_GET,
                ),
            ],
            [
                ib(
                    " Manage Services",
                    callback_data="adm:services",
                    style="primary",
                    emoji_id=E_STATUS,
                ),
                ib(
                    " Withdrawal Nodes",
                    callback_data="adm:withdrawals",
                    style="primary",
                    emoji_id=E_ACTIVE,
                ),
            ],
            [
                ib(
                    "📢 PUSH Broadcast",
                    callback_data="adm:broadcast",
                    style="primary",
                    emoji_id=E_STATUS,
                ),
                ib(
                    " Admins Configuration",
                    callback_data="adm:admins",
                    style="primary",
                    emoji_id=E_ADMIN,
                ),
            ],
            [
                ib(
                    " Add System Admin",
                    callback_data="adm:addadmin",
                    style="success",
                    emoji_id=E_GET,
                ),
                ib(
                    " Decouple Admin Node",
                    callback_data="adm:removeadmin",
                    style="danger",
                    emoji_id=E_ADMIN,
                ),
            ],
            [
                ib(
                    " Requirements Channel",
                    callback_data="adm:reqchannel",
                    style="primary",
                    emoji_id=E_SUPPORT,
                ),
                ib(
                    " Global Configurations",
                    callback_data="adm:settings",
                    style="primary",
                    emoji_id=E_STATUS,
                ),
            ],
        ]
    )

# =========================================================
# MEMBERSHIP
# =========================================================

async def verify_dual_membership(
    bot,
    user_id: int,
) -> bool:

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS global_config (
                    config_key TEXT PRIMARY KEY,
                    config_value TEXT
                )
                """
            )

            await db.commit()

            async with db.execute(
                """
                SELECT config_value
                FROM global_config
                WHERE config_key = 'req_channel'
                """
            ) as cursor:

                row = await cursor.fetchone()

        db_channel = (
            row["config_value"]
            if row
            else UPDATE_CHANNEL_LINK
        )

        channel_value = str(
            db_channel or ""
        ).strip()

        if channel_value.startswith("-100"):
            target_channel = int(channel_value)

        elif "t.me/" in channel_value:
            clean = channel_value.split(
                "t.me/",
                1,
            )[-1].strip("/")

            if clean.startswith("+"):
                return False

            if "joinchat/" in clean:
                return False

            target_channel = (
                clean
                if clean.startswith("@")
                else f"@{clean}"
            )

        else:
            target_channel = (
                channel_value
                if channel_value.startswith("@")
                else f"@{channel_value}"
            )

        channel_member = await bot.get_chat_member(
            chat_id=target_channel,
            user_id=user_id,
        )

        if channel_member.status in {
            "left",
            "kicked",
        }:
            return False

        group_member = await bot.get_chat_member(
            chat_id=OTP_GROUP_ID,
            user_id=user_id,
        )

        if group_member.status in {
            "left",
            "kicked",
        }:
            return False

        return True

    except Exception:
        logger.exception(
            "Membership verification failed for %s",
            user_id,
        )
        return False


# =========================================================
# JOIN KEYBOARD
# =========================================================

def generate_join_inline_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                ib(
                    " Join Official Channel",
                    url=UPDATE_CHANNEL_LINK,
                    style="primary",
                    emoji_id=E_SUPPORT,
                )
            ],
            [
                ib(
                    " Join Method Channel",
                    url=EXTRA_LINK_1,
                    style="primary",
                    emoji_id=E_SUPPORT,
                )
            ],
            [
                ib(
                    " Join Payment Proofs",
                    url=EXTRA_LINK_2,
                    style="primary",
                    emoji_id=E_SUPPORT,
                )
            ],
            [
                ib(
                    " Join Official OTP Group",
                    url=OTP_GROUP_LINK,
                    style="primary",
                    emoji_id=E_GROUP,
                )
            ],
            [
                ib(
                    " Try Again / VERIFY",
                    callback_data="membership:retry",
                    style="success",
                    emoji_id=E_VERIFY,
                )
            ],
        ]
    )


async def deny_access(
    bot,
    user_id: int,
):
    await send_msg(
        bot,
        user_id,
        (
            f"{SYS_EMOJI}  "
            f"<b>Access Denied!</b>\n\n"
            f"Please join both the official channel "
            f"and OTP group first."
        ),
        generate_join_inline_keyboard(),
    )


async def require_admin(
    callback: types.CallbackQuery,
) -> bool:

    try:
        return await db_mgr.is_admin(
            callback.from_user.id
        )
    except Exception:
        return False


async def service_selection_keyboard():

    categories = await db_mgr.get_categories()

    keyboard = []

    for category in categories:
        name = str(category["name"]).strip()

        keyboard.append(
            [
                ib(
                    f"{get_service_placeholder(name)} "
                    f"{name.upper()}",
                    callback_data=pack_callback(
                        "buy",
                        name,
                    ),
                    style="success",
                    emoji_id=get_service_custom_emoji_id(name),
                )
            ]
        )

    keyboard.append(
        [
            ib(
                " Main Menu",
                callback_data="menu:main",
                style="primary",
                emoji_id=E_BACK,
            )
        ]
    )

    return (
        categories,
        InlineKeyboardMarkup(
            inline_keyboard=keyboard
        ),
    )


def number_result_keyboard(
    service: str,
    country: str,
    allocated: list[str],
    cc_mode: str,
):

    rows = []

    country_emoji = get_country_custom_emoji_id(
        country
    )

    for number in allocated:

        display_number = (
            extract_pure_number_without_cc(
                number,
                country,
            )
            if cc_mode == "ON"
            else number
        )

        copied = (
            display_number
            if cc_mode == "ON"
            else f"+{display_number}"
        )

        rows.append(
            [
                ib(
                    f"{display_number}",
                    copy_text=copied,
                    style="primary",
                    emoji_id=country_emoji,
                )
            ]
        )

    cc_text = (
        "Remove CC: ON"
        if cc_mode == "ON"
        else "Remove CC: OFF"
    )

    rows.extend(
        [
            [
                ib(
                    "Change Number",
                    callback_data=pack_callback(
                        "change",
                        service,
                        country,
                    ),
                    style="primary",
                    emoji_id=E_CHANGE,
                )
            ],
            [
                ib(
                    cc_text,
                    callback_data=pack_callback(
                        "cc",
                        service,
                        country,
                    ),
                    style="success",
                    emoji_id=E_CC,
                )
            ],
            [
                ib(
                    "Main Menu",
                    callback_data="menu:main",
                    style="primary",
                    emoji_id=E_BACK,
                )
            ],
            [
                ib(
                    "OTP Group",
                    url=OTP_GROUP_LINK,
                    style="danger",
                    emoji_id=E_GROUP,
                )
            ],
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def number_result_text(
    service: str,
    country: str,
):
    try:
        s_emoji_id = get_service_custom_emoji_id(service)
        s_emoji = f'<tg-emoji emoji-id="{s_emoji_id}">✅</tg-emoji>'
    except Exception:
        s_emoji = '✅'

    try:
        c_emoji_id = get_country_custom_emoji_id(country)
        c_emoji = f'<tg-emoji emoji-id="{c_emoji_id}">🌍</tg-emoji>'
    except Exception:
        c_emoji = '🌍'

    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    premium = "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝗪𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝗶𝐣𝗸𝗹𝗺𝗻𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝘃𝘄𝘅𝘆𝘇"
    premium_service = service.upper().translate(str.maketrans(normal, premium))

    return (
        f'<tg-emoji emoji-id="6206236607532504295">💼</tg-emoji> <i><b>Service:</b></i> {s_emoji} <b>{premium_service}</b>\n'
        f'<tg-emoji emoji-id="6114021507908767611">🌎</tg-emoji> <i><b>Country:</b></i> {c_emoji} <b>{country.capitalize()}</b>\n\n'
        f'<tg-emoji emoji-id="5386367538735104399">⌛</tg-emoji> <b>Waiting for OTP</b>'
    )


async def show_allocated_numbers(
    message: types.Message,
    service: str,
    country: str,
    allocated: list[str],
):

    cc_mode = await db_mgr.get_config(
        "remove_cc"
    )

    text = number_result_text(
        service,
        country,
    )

    keyboard = number_result_keyboard(
        service,
        country,
        allocated,
        cc_mode,
    )

    await safe_edit(
        message,
        text,
        keyboard,
    )


@router.callback_query(
    F.data == "membership:retry"
)
async def process_membership_retry(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    if not await verify_dual_membership(
        callback.bot,
        callback.from_user.id,
    ):
        await safe_answer(
            callback,
            " You have not joined both yet.",
            show_alert=True,
        )
        return

    await state.clear()

    is_admin = await db_mgr.is_admin(
        callback.from_user.id
    )

    await send_msg(
        callback.bot,
        callback.from_user.id,
        (
            f"{SYS_EMOJI}  "
            f"<b>Verification Successful!</b>\n\n"
            f"Welcome to the Elite 24/7 OTP Engine."
        ),
        main_permanent_keyboard(
            callback.from_user.id,
            is_admin,
        ),
    )

    try:
        await callback.message.delete()
    except Exception:
        pass

    await safe_answer(
        callback,
        "✅ Verified!",
    )


@router.callback_query(
    F.data == "menu:main"
)
async def callback_menu_main(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    if not await verify_dual_membership(
        callback.bot,
        callback.from_user.id,
    ):
        await deny_access(
            callback.bot,
            callback.from_user.id,
        )
        await safe_answer(
            callback,
            "⚠️ Access denied.",
            show_alert=True,
        )
        return

    await state.clear()

    categories, keyboard = (
        await service_selection_keyboard()
    )

    if not categories:
        await safe_edit(
            callback.message,
            (
                f"{SYS_EMOJI}  "
                f"<b>No active services.</b>\n\n"
                f"Please try again later."
            ),
        )
        await safe_answer(callback)
        return

    await safe_edit(
        callback.message,
        (
            '<tg-emoji emoji-id="6206236607532504295">💼</tg-emoji> <b>Select service</b> <tg-emoji emoji-id="5197474438970363734">⤵️</tg-emoji>\n\n'
            'Choose a service to get a number:'
        ),
        keyboard,
    )

    await safe_answer(callback)


@router.callback_query(
    F.data.startswith("buy:")
)
async def process_allocation_service(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    if not await verify_dual_membership(
        callback.bot,
        callback.from_user.id,
    ):
        await deny_access(
            callback.bot,
            callback.from_user.id,
        )
        await safe_answer(
            callback,
            " Access denied.",
            show_alert=True,
        )
        return

    await state.clear()

    values = unpack_callback(
        callback.data,
        "buy",
    )

    if not values:
        await safe_answer(
            callback,
            "❌ Invalid service.",
            show_alert=True,
        )
        return

    service = values[0].strip().upper()

    # 🔥 ডাটাবেস থেকে স্টক এবং গত ১০ মিনিটের লাইভ ট্রাফিক চেক
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # ১. শুধুমাত্র 0 এর থেকে বেশি স্টক আছে এমন কান্ট্রিগুলো বের করা
        cursor = await db.execute("""
            SELECT country, COUNT(phone_number) as stock_count 
            FROM numbers_pool 
            WHERE UPPER(service) = ? 
            AND (assigned_to = 0 OR assigned_to IS NULL)
            GROUP BY UPPER(country)
            HAVING stock_count > 0
            ORDER BY country ASC
        """, (service,))
        country_rows = await cursor.fetchall()

        # ২. 🕒 গত ১০ মিনিটে কোন কান্ট্রিগুলোতে নতুন OTP এসেছে সেটা চেক করা হচ্ছে
        cursor_traffic = await db.execute("""
            SELECT DISTINCT UPPER(n.country) 
            FROM otp_history o
            JOIN numbers_pool n ON o.phone_number = n.phone_number
            WHERE UPPER(o.service) = ? AND datetime(o.timestamp) >= datetime('now', '-10 minute')
        """, (service,))
        traffic_rows = await cursor_traffic.fetchall()
        
        # ট্রাফিক থাকা কান্ট্রিগুলোর লিস্ট
        active_traffic_countries = {str(row[0]).strip() for row in traffic_rows}

    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    premium = "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝗪𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝗶𝐣𝗸𝗹𝗺𝗻𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝘃𝘄𝘅𝘆𝘇"
    premium_service = service.translate(str.maketrans(normal, premium))

    if not country_rows:
        await safe_edit(
            callback.message,
            (
                f'<tg-emoji emoji-id="5420323339723881652">⚠️</tg-emoji> <b>OUT OF STOCK</b>\n\n'
                f"No stock available for "
                f"<b>{premium_service}</b>."
            ),
        )

        await safe_answer(
            callback,
            "No stock available.",
            show_alert=True,
        )
        return

    rows = []
    current_row = []

    for row in country_rows:
        country_name = str(row["country"]).strip()
        stock = int(row["stock_count"])
        
        c_upper = country_name.upper()
        premium_country = c_upper.translate(str.maketrans(normal, premium))

        # 🔥 আল্টিমেট ডিসিশন মেকার: গত ১০ মিনিটে ট্রাফিক থাকলে সবুজ (success), না থাকলে নীল (primary)
        if c_upper in active_traffic_countries:
            btn_style = "success"
        else:
            btn_style = "primary"

        btn = ib(
            f" {premium_country} ({stock})",
            callback_data=pack_callback(
                "country",
                service,
                country_name,
            ),
            style=btn_style,
            emoji_id=get_country_custom_emoji_id(country_name),
        )
        
        current_row.append(btn)

        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []

    if current_row:
        rows.append(current_row)

    # 🔥 শুধুমাত্র মেইন মেনুতে যাওয়ার ব্যাক বাটন (রিফ্রেশ বাটন গায়েব)
    rows.append(
        [
            ib(
                " Back",
                callback_data="menu:main",
                style="primary",
                emoji_id=E_BACK,
            )
        ]
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=rows
    )

    try:
        s_emo_id = get_service_custom_emoji_id(service)
        s_emo = f'<tg-emoji emoji-id="{s_emo_id}">💬</tg-emoji>'
    except Exception:
        s_emo = '💬'

    await safe_edit(
        callback.message,
        (
            f'<tg-emoji emoji-id="5409048419211682843">💠</tg-emoji> <b>Service:</b> {s_emo} <b>{premium_service}</b>\n\n'
            f'<b>Select a country from available stock:</b>'
        ),
        keyboard,
    )

    await safe_answer(callback)

@router.callback_query(
    F.data.startswith("country:")
)
async def process_allocation_final(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    if not await verify_dual_membership(
        callback.bot,
        callback.from_user.id,
    ):
        await deny_access(
            callback.bot,
            callback.from_user.id,
        )
        await safe_answer(
            callback,
            " Access denied.",
            show_alert=True,
        )
        return

    values = unpack_callback(
        callback.data,
        "country",
    )

    if len(values) != 2:
        await safe_answer(
            callback,
            " Invalid country selection.",
            show_alert=True,
        )
        return

    service = values[0].strip().upper()
    country = values[1].strip()

    categories = await db_mgr.get_categories()

    cat_spec = next(
        (
            c
            for c in categories
            if str(c["name"]).upper()
            == service
        ),
        None,
    )

    if not cat_spec:
        await safe_answer(
            callback,
            "❌ Service configuration unavailable.",
            show_alert=True,
        )
        return

    await safe_answer(
        callback,
        "⏳ Allocating number...",
    )

    allocated = (
        await db_mgr.allocate_numbers_to_user(
            callback.from_user.id,
            service,
            country,
            cat_spec["nums_per_user"],
        )
    )

    if not allocated:
        await safe_edit(
            callback.message,
            (
                f" <b>OUT OF STOCK</b>\n\n"
                f"No numbers left for "
                f"<b>{service}</b> "
                f"({country})."
            ),
        )
        return

    await show_allocated_numbers(
        callback.message,
        service,
        country,
        allocated,
    )

@router.callback_query(
    F.data.startswith("change:")
)
async def process_change_number(
    callback: types.CallbackQuery,
):
    if not await verify_dual_membership(
        callback.bot,
        callback.from_user.id,
    ):
        await deny_access(
            callback.bot,
            callback.from_user.id,
        )
        return await safe_answer(
            callback,
            " Access denied.",
            show_alert=True,
        )

    # 🔥 Database Columns Auto-Migration (Ultra Safe - Separate Blocks)
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
        except Exception: pass
        try:
            # wasted_count কে এখন আমরা Spam Click Tracker হিসেবে ইউজ করবো
            await db.execute("ALTER TABLE users ADD COLUMN wasted_count INTEGER DEFAULT 0")
        except Exception: pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN last_number_time REAL DEFAULT 0")
        except Exception: pass
        
        await db.commit()
        
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (callback.from_user.id,))
        user_data = await cursor.fetchone()

    user_dict = dict(user_data) if user_data else {}

    # 🚫 Ban Check First
    if user_dict.get('is_banned', 0):
        return await safe_answer(callback, "🚫 You are permanently BANNED for abusing the system!", show_alert=True)

    # ⏱️ 15-Second Cooldown & 5-Click Spam Check
    current_time = time.time()
    last_time = user_dict.get('last_number_time', 0)
    if not last_time: 
        last_time = 0
        
    time_diff = current_time - float(last_time)
    spam_count = user_dict.get('wasted_count', 0)
    if not spam_count:
        spam_count = 0

    if time_diff < 15.0:
        spam_count += 1
        
        if spam_count >= 5:
            # 🛑 5 বার স্প্যাম ক্লিক করলেই ডাইরেক্ট পার্মানেন্ট ব্যান
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE users SET is_banned = 1, wasted_count = ? WHERE user_id = ?", (spam_count, callback.from_user.id))
                await db.commit()
                
            # Notify Admins
            normal_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
            premium_chars = "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"
            font_map = str.maketrans(normal_chars, premium_chars)
            
            username = f"@{callback.from_user.username}" if callback.from_user.username else "No Username"
            u_name = callback.from_user.first_name
            
            alert_text = (
                f'<tg-emoji emoji-id="5420323339723881652">⚠️</tg-emoji> <b>{"SPAM ABUSE DETECTED".translate(font_map)}</b>\n\n'
                f'{"This user has been permanently banned for button spamming".translate(font_map)}.\n\n'
                f'<tg-emoji emoji-id="5453957997418004470">👤</tg-emoji> {"Name".translate(font_map)}: <b>{str(u_name).translate(font_map)}</b>\n'
                f'<tg-emoji emoji-id="5354972242629383937">🆔</tg-emoji> {"UID".translate(font_map)}: <code>{str(callback.from_user.id).translate(font_map)}</code>\n'
                f'<tg-emoji emoji-id="6275857834127134596">🔗</tg-emoji> {"Username".translate(font_map)}: {username.translate(font_map)}'
            )
            
            admin_kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        ib("Unban User".translate(font_map), callback_data=f"sys_unban:{callback.from_user.id}", style="success", emoji_id="5472250091332993630"),
                        ib("Notice User".translate(font_map), callback_data=f"sys_notice:{callback.from_user.id}", style="primary", emoji_id="6269532506941298061")
                    ]
                ]
            )
            
            admins = await db_mgr.get_admins() if hasattr(db_mgr, 'get_admins') else []
            for admin_id in admins:
                try:
                    await callback.bot.send_message(chat_id=admin_id, text=alert_text, reply_markup=admin_kb)
                except Exception:
                    pass

            return await safe_answer(callback, "🚫 BANNED: You spammed the button too many times!", show_alert=True)
            
        else:
            # স্প্যাম কাউন্ট আপডেট করে ওয়ার্নিং দেওয়া হচ্ছে
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE users SET wasted_count = ? WHERE user_id = ?", (spam_count, callback.from_user.id))
                await db.commit()
                
            wait_time = int(15 - time_diff)
            return await safe_answer(callback, f"⚠️ Please wait {wait_time}s! Spamming will get you banned ({spam_count}/5)", show_alert=True)

    # ⏳ ১৫ সেকেন্ড পার হয়ে গেলে নরমাল চেঞ্জ অ্যাকসেপ্ট হবে এবং স্প্যাম কাউন্ট জিরো হয়ে যাবে
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET last_number_time = ?, wasted_count = 0 WHERE user_id = ?", (current_time, callback.from_user.id))
        await db.commit()

    # Original Allocation Logic
    values = unpack_callback(
        callback.data,
        "change",
    )

    if len(values) != 2:
        return await safe_answer(callback, " Invalid request.", show_alert=True)

    service = values[0].strip().upper()
    country = values[1].strip()

    await safe_answer(callback, " Changing number...")

    try:
        await db_mgr.clear_user_numbers(
            callback.from_user.id,
            service,
        )
    except Exception:
        pass

    categories = await db_mgr.get_categories()
    cat_spec = next((c for c in categories if str(c["name"]).upper() == service), None)

    if not cat_spec:
        return await safe_edit(callback.message, " Selected service is unavailable.")

    allocated = await db_mgr.allocate_numbers_to_user(
        callback.from_user.id,
        service,
        country,
        cat_spec["nums_per_user"],
    )

    if not allocated:
        return await safe_edit(callback.message, f" <b>OUT OF STOCK</b>\n\nNo numbers left for {service} ({country}).")

    await show_allocated_numbers(
        callback.message,
        service,
        country,
        allocated,
    )

@router.callback_query(
    F.data.startswith("cc:")
)
async def user_toggle_cc(
    callback: types.CallbackQuery,
):

    if not await verify_dual_membership(
        callback.bot,
        callback.from_user.id,
    ):
        await deny_access(
            callback.bot,
            callback.from_user.id,
        )
        await safe_answer(
            callback,
            " Access denied.",
            show_alert=True,
        )
        return

    values = unpack_callback(
        callback.data,
        "cc",
    )

    if len(values) != 2:
        await safe_answer(
            callback,
            " Invalid request.",
            show_alert=True,
        )
        return

    service = values[0].strip().upper()
    country = values[1].strip()

    new_status = await db_mgr.toggle_config(
        "remove_cc"
    )

    categories = await db_mgr.get_categories()

    cat_spec = next(
        (
            c
            for c in categories
            if str(c["name"]).upper()
            == service
        ),
        None,
    )

    quota = (
        cat_spec["nums_per_user"]
        if cat_spec
        else None
    )

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        query = """
            SELECT phone_number
            FROM numbers_pool
            WHERE assigned_to = ?
              AND service = ?
              AND UPPER(country) = UPPER(?)
            ORDER BY assigned_at DESC
        """

        params = [
            callback.from_user.id,
            service,
            country,
        ]

        if quota:
            query += " LIMIT ?"
            params.append(quota)

        async with db.execute(
            query,
            params,
        ) as cursor:

            rows = await cursor.fetchall()

    allocated = [
        row["phone_number"]
        for row in rows
    ]

    if not allocated:
        await safe_answer(
            callback,
            "No active number session found.",
            show_alert=True,
        )
        return

    await safe_edit(
        callback.message,
        number_result_text(
            service,
            country,
        ),
        number_result_keyboard(
            service,
            country,
            allocated,
            new_status,
        ),
    )

    await safe_answer(
        callback,
        f"Remove CC is now {new_status}.",
    )


# 🔥 নতুন ক্লোজ/হোম হ্যান্ডলার (ব্যাক দিলে এই মেসেজটা আসবে)
@router.callback_query(F.data == "menu:close")
async def callback_menu_close(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(
        callback.message,
        (
            f"{SYS_EMOJI} "
            f"<b>Action cancelled.</b>\n\n"
            f"Please use the menu buttons below."
        )
    )
    await safe_answer(callback)

# 🔥 আপনার আপডেট করা ওয়ালেট সেট ফাংশন
@router.callback_query(
    F.data == "wallet:set"
)
async def user_req_set_wallet(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                ib(
                    " Bkash",
                    callback_data="wallet:bkash",
                    style="primary",
                    emoji_id="5348469219761626211",
                ),
                ib(
                    " Nagad",
                    callback_data="wallet:nagad",
                    style="primary",
                    emoji_id="6147706485439730700",
                ),
            ],
            [
                ib(
                    " Rocket",
                    callback_data="wallet:rocket",
                    style="primary",
                    emoji_id="5346042941196507141",
                ),
                ib(
                    " Binance",
                    callback_data="wallet:binance",
                    style="primary",
                    emoji_id="5348212415077064131",
                ),
            ],
            [
                # 🔥 ম্যাজিক! ব্যাক বাটন এখন "menu:close" এ যাবে
                ib(
                    " Back",
                    callback_data="menu:close",
                    style="primary",
                    emoji_id=E_BACK,
                )
            ],
        ]
    )

    await safe_edit(
        callback.message,
        (
            f"{SYS_EMOJI}  "
            f"<b>Choose Wallet Provider</b>"
        ),
        keyboard,
    )

    await safe_answer(callback)


@router.callback_query(
    F.data.startswith("wallet:")
)
async def user_select_wallet_provider(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    method = callback.data.split(
        ":",
        1,
    )[1]

    if method == "view":
        await safe_answer(callback)
        return

    method = method.title()

    await state.update_data(
        wallet_type=method
    )

    await state.set_state(
        Form.waiting_for_set_wallet_number
    )

    if method in {
        "Bkash",
        "Nagad",
        "Rocket",
    }:
        prompt = (
            f" Send your "
            f"<b>{method}</b> number:"
        )
    else:
        prompt = (
            f" Send your "
            f"<b>{method}</b> Pay ID "
        )

    await send_msg(
        callback.bot,
        callback.from_user.id,
        (
            f"{SYS_EMOJI}  {prompt}\n\n"
            f"Send <b>/cancel</b> to stop."
        ),
    )

    await safe_answer(callback)


@router.callback_query(
    F.data == "withdraw:start"
)
async def user_start_withdraw_flow(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    await state.clear()

    withdraw_status = await db_mgr.get_config(
        "withdraw_enabled"
    )

    if str(withdraw_status).upper() == "OFF":
        await safe_answer(
            callback,
            " Withdraw is disabled by admin.",
            show_alert=True,
        )
        return

    user = await db_mgr.get_user(
        callback.from_user.id
    )

    if not user:
        await safe_answer(
            callback,
            " User profile not found.",
            show_alert=True,
        )
        return

    if (
        not user.get("wallet_type")
        or not user.get("wallet_number")
    ):
        await safe_answer(
            callback,
            " Set your wallet first.",
            show_alert=True,
        )
        return

    await state.set_state(
        Form.waiting_for_withdraw_amt
    )

    await send_msg(
        callback.bot,
        callback.from_user.id,
        (
            f"{SYS_EMOJI}  "
            f"<b>Send withdrawal amount (USD)</b>\n\n"
            f"Example: <code>10</code>\n"
            f"Send <b>/cancel</b> to stop."
        ),
    )

    await safe_answer(callback)


def settings_keyboard(
    withdraw_status: str,
):

    status = str(
        withdraw_status or "OFF"
    ).upper()

    text = (
        " Withdraw: ON"
        if status == "ON"
        else
        " Withdraw: OFF"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                ib(
                    " Edit Support User",
                    callback_data="settings:support",
                    style="primary",
                    emoji_id=E_SUPPORT,
                ),
                ib(
                    " Edit Min Withdraw",
                    callback_data="settings:minw",
                    style="primary",
                    emoji_id=E_WALLET,
                ),
            ],
            [
                ib(
                    text,
                    callback_data="settings:toggle",
                    style="success",
                    emoji_id=E_STATUS,
                )
            ],
            [
                ib(
                    " Back To Panel",
                    callback_data="admin:panel",
                    style="primary",
                    emoji_id=E_BACK,
                )
            ],
        ]
    )


@router.callback_query(
    F.data == "adm:settings"
)
async def adm_open_settings(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    if not await require_admin(callback):
        await safe_answer(
            callback,
            " Admin only.",
            show_alert=True,
        )
        return

    await state.clear()

    status = await db_mgr.get_config(
        "withdraw_enabled"
    )

    await safe_edit(
        callback.message,
        (
            " <b>System Settings</b>\n\n"
            "Manage global bot configuration:"
        ),
        settings_keyboard(status),
    )

    await safe_answer(callback)


@router.callback_query(
    F.data == "settings:toggle"
)
async def adm_toggle_withdraw(
    callback: types.CallbackQuery,
):

    if not await require_admin(callback):
        await safe_answer(
            callback,
            " Admin only.",
            show_alert=True,
        )
        return

    new_status = await db_mgr.toggle_config(
        "withdraw_enabled"
    )

    await safe_edit(
        callback.message,
        (
            " <b>System Settings</b>\n\n"
            "Withdraw system status updated."
        ),
        settings_keyboard(new_status),
    )

    await safe_answer(
        callback,
        f"Withdraw is now {new_status}",
    )


@router.callback_query(
    F.data == "settings:support"
)
async def adm_edit_support(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    if not await require_admin(callback):
        await safe_answer(
            callback,
            " Admin only.",
            show_alert=True,
        )
        return

    await state.set_state(
        Form.waiting_for_edit_support
    )

    await send_msg(
        callback.bot,
        callback.from_user.id,
        (
            " <b>Send new support username</b>\n\n"
            "Example: <code>support</code>"
        ),
    )

    await safe_answer(callback)


@router.callback_query(
    F.data == "settings:minw"
)
async def adm_edit_minw(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    if not await require_admin(callback):
        await safe_answer(
            callback,
            " Admin only.",
            show_alert=True,
        )
        return

    await state.set_state(
        Form.waiting_for_edit_min_with
    )

    await send_msg(
        callback.bot,
        callback.from_user.id,
        (
            " <b>Send minimum withdrawal amount</b>\n\n"
            "Example: <code>5</code>"
        ),
    )

    await safe_answer(callback)


@router.callback_query(
    F.data == "admin:panel"
)
async def back_to_admin_panel(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    if not await require_admin(callback):
        await safe_answer(
            callback,
            " Admin only.",
            show_alert=True,
        )
        return

    await state.clear()

    await safe_edit(
        callback.message,
        (
            f"{SYS_EMOJI}  "
            f"<b>Administrative Command Hub</b>"
        ),
        admin_inline_panel(),
    )

    await safe_answer(callback)


@router.callback_query(
    F.data == "adm:addservice"
)
async def adm_start_add_service(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    if not await require_admin(callback):
        await safe_answer(
            callback,
            " Admin only.",
            show_alert=True,
        )
        return

    await state.clear()
    await state.set_state(
        Form.waiting_for_new_service
    )

    await send_msg(
        callback.bot,
        callback.from_user.id,
        (
            " <b>Send the new service name:</b>\n\n"
            "Example: <code>Snapchat</code>"
        ),
    )

    await safe_answer(callback)


@router.callback_query(
    F.data == "adm:addnum"
)
async def adm_start_add_numbers(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    if not await require_admin(callback):
        await safe_answer(
            callback,
            " Admin only.",
            show_alert=True,
        )
        return

    await state.clear()

    await state.set_state(
        Form.waiting_for_numbers
    )

    await send_msg(
        callback.bot,
        callback.from_user.id,
        (
            " <b>Add Numbers</b>\n\n"
            "<b>Step 1:</b>\n"
            "Send numbers one per line, comma separated, "
            "space separated, or upload TXT/CSV.\n\n"
            "Example:\n"
            "<code>8801712345678\n"
            "8801812345678</code>"
        ),
    )

    await safe_answer(callback)


@router.callback_query(F.data == "adm:inventory")
async def adm_inventory_menu(callback: types.CallbackQuery):
    if not await db_mgr.is_admin(callback.from_user.id):
        return await safe_answer(callback, "Admin only", show_alert=True)
        
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT DISTINCT service FROM numbers_pool")
        rows = await cursor.fetchall()
        
    if not rows:
        await safe_edit(callback.message, " <b>Inventory is completely empty.</b>", admin_inline_panel())
        return
        
    keyboard = []
    for row in rows:
        svc = str(row[0]).upper()
        try:
            s_emoji = get_service_custom_emoji_id(svc)
        except Exception:
            s_emoji = E_STATUS
            
        cb_data = pack_callback("delsvc", svc)
        keyboard.append([ib(f" Delete from {svc}", callback_data=cb_data, style="danger", emoji_id=s_emoji)])
        
    keyboard.append([ib(" Back To Panel", callback_data="admin:panel", style="primary", emoji_id=E_BACK)])
        
    await safe_edit(
        callback.message, 
        " <b>Inventory Dashboard</b>\n\nSelect a service to view and delete specific countries:", 
        InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(F.data.startswith("delsvc:"))
async def delete_stock_select_country(callback: types.CallbackQuery):
    if not await db_mgr.is_admin(callback.from_user.id):
        return await safe_answer(callback, "Admin only", show_alert=True)
        
    unpacked = unpack_callback(callback.data, "delsvc")
    if not unpacked:
        return await safe_answer(callback, "Error parsing data", show_alert=True)
        
    service = unpacked[0].upper()
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT country, COUNT(*) FROM numbers_pool WHERE UPPER(service) = ? GROUP BY country", 
            (service,)
        )
        rows = await cursor.fetchall()
        
    if not rows:
        await safe_answer(callback, f"No stock found for {service}", show_alert=True)
        return
        
    keyboard = []
    for row in rows:
        country = str(row[0])
        count = row[1]
        try:
            c_emoji = get_country_custom_emoji_id(country)
        except Exception:
            c_emoji = E_ADMIN
            
        cb_data = pack_callback("delcty", service, country)
        keyboard.append([ib(f" {country} ({count} nums)", callback_data=cb_data, style="danger", emoji_id=c_emoji)])
        
    keyboard.append([ib(" Back to Services", callback_data="adm:inventory", style="primary", emoji_id=E_BACK)])
    
    await safe_edit(
        callback.message, 
        f" <b>Select Country to Delete from {service}</b>", 
        InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(F.data.startswith("delcty:"))
async def delete_stock_confirm(callback: types.CallbackQuery):
    if not await db_mgr.is_admin(callback.from_user.id):
        return
        
    unpacked = unpack_callback(callback.data, "delcty")
    if len(unpacked) != 2:
        return await safe_answer(callback, "Error parsing data", show_alert=True)
        
    service, country = unpacked
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM numbers_pool WHERE UPPER(service) = ? AND UPPER(country) = ?", 
            (service.upper(), country.upper())
        )
        row = await cursor.fetchone()
        count = row[0] if row else 0
        
    text = (
        f" <b>WARNING: DELETION CONFIRMATION</b>\n\n"
        f"<b>Service:</b> <code>{service.upper()}</code>\n"
        f"<b>Country:</b> <code>{country}</code>\n"
        f"<b>Numbers to delete:</b> <code>{count}</code>\n\n"
        f"Are you sure you want to delete these numbers? This action cannot be undone."
    )
    
    cb_yes = pack_callback("delyes", service, country)
    cb_no = pack_callback("delsvc", service)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            ib(" YES, DELETE", callback_data=cb_yes, style="danger", emoji_id=E_VERIFY),
            ib(" NO, CANCEL", callback_data=cb_no, style="primary", emoji_id=E_BACK)
        ]
    ])
    
    await safe_edit(callback.message, text, keyboard)


@router.callback_query(F.data.startswith("delyes:"))
async def delete_stock_execute(callback: types.CallbackQuery):
    if not await db_mgr.is_admin(callback.from_user.id):
        return
        
    unpacked = unpack_callback(callback.data, "delyes")
    if len(unpacked) != 2:
        return await safe_answer(callback, "Error parsing data", show_alert=True)
        
    service, country = unpacked
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM numbers_pool WHERE UPPER(service) = ? AND UPPER(country) = ?", 
            (service.upper(), country.upper())
        )
        await db.commit()
        
    await safe_answer(callback, f"Deleted {country} from {service.upper()}", show_alert=True)
    await safe_edit(
        callback.message, 
        f" Successfully deleted all <b>{country}</b> numbers from <b>{service.upper()}</b>.", 
        admin_inline_panel()
    )


@router.callback_query(F.data == "adm:services")
async def adm_manage_categories(callback: types.CallbackQuery, state: FSMContext):
    if not await require_admin(callback):
        return await safe_answer(callback, " Admin only.", show_alert=True)
    await state.clear()
    cats = await db_mgr.get_categories()
    
    text = f" <b>Manage Services</b>\n\nTotal active: <code>{len(cats)}</code>\n\n"
    rows = []
    
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    premium = "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝗪𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝗶𝐣𝗸𝗹𝗺𝗻𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝘃𝘄𝗫𝘆𝘇"
    
    for category in cats:
        name = str(category["name"])
        premium_name = name.upper().translate(str.maketrans(normal, premium))
        
        quota = category.get("nums_per_user", 0)
        rate = category.get("rate_per_otp", 0)
        
        text += f"▪️ <b>{premium_name}</b>\n   Quota: <code>{quota}</code>\n   Rate: <code>{rate}$</code>\n\n"
        rows.append([
            ib(f" Edit Rate {premium_name}", callback_data=pack_callback("editrate", name), style="success", emoji_id=E_CHANGE),
            ib(f" Remove {premium_name}", callback_data=pack_callback("rmservice", name), style="danger", emoji_id=E_ADMIN)
        ])
        
    rows.append([ib(" Back", callback_data="admin:panel", style="primary", emoji_id=E_BACK)])
    
    await safe_edit(callback.message, text, InlineKeyboardMarkup(inline_keyboard=rows))
    await safe_answer(callback)


@router.callback_query(F.data.startswith("editrate:"))
async def adm_edit_rate_start(callback: types.CallbackQuery, state: FSMContext):
    if not await require_admin(callback):
        return await safe_answer(callback, " Admin only.", show_alert=True)
        
    values = unpack_callback(callback.data, "editrate")
    if not values: return
    
    service = values[0].upper()
    await state.update_data(editing_service=service)
    await state.set_state(Form.waiting_for_edit_service_rate)
    
    await send_msg(
        callback.bot, callback.from_user.id,
        f" <b>Edit Rate for {service}</b>\n\nSend the new rate per OTP in USD (e.g., <code>0.08</code>):"
    )
    await safe_answer(callback)


@router.callback_query(
    F.data.startswith("rmservice:")
)
async def adm_remove_category(
    callback: types.CallbackQuery,
):

    if not await require_admin(callback):
        await safe_answer(
            callback,
            " Admin only.",
            show_alert=True,
        )
        return

    values = unpack_callback(
        callback.data,
        "rmservice",
    )

    if not values:
        await safe_answer(
            callback,
            "Invalid service.",
            show_alert=True,
        )
        return

    service = values[0]

    await db_mgr.remove_category(
        service
    )

    await safe_edit(
        callback.message,
        (
            f" <b>Service removed</b>\n\n"
            f"Service: <code>{service}</code>"
        ),
        InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    ib(
                        " Services",
                        callback_data="adm:services",
                        style="primary",
                        emoji_id=E_BACK,
                    )
                ]
            ]
        ),
    )

    await safe_answer(
        callback,
        "Service removed.",
    )


@router.callback_query(
    F.data == "adm:withdrawals"
)
async def adm_view_withdrawals(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    if not await require_admin(callback):
        await safe_answer(
            callback,
            " Admin only.",
            show_alert=True,
        )
        return

    await state.clear()

    reqs = await db_mgr.get_pending_withdrawals()

    if not reqs:
        await safe_edit(
            callback.message,
            (
                " <b>Pending Withdrawals</b>\n\n"
                " No pending requests."
            ),
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        ib(
                            " Back",
                            callback_data="admin:panel",
                            style="primary",
                            emoji_id=E_BACK,
                        )
                    ]
                ]
            ),
        )

        await safe_answer(callback)
        return

    await safe_answer(
        callback,
        f"{len(reqs)} pending request(s).",
    )

    for req in reqs:

        method = str(
            req.get("method")
            or "N/A"
        ).title()

        wallet = str(
            req.get("wallet_number")
            or "N/A"
        )

        text = (
            " <b>Withdrawal Request</b>\n\n"
            f" Node ID: <code>{req['id']}</code>\n"
            f" User ID: <code>{req['user_id']}</code>\n"
            f" Amount: <code>{req['amount']}$</code>\n"
            f" Method: <code>{method}</code>\n"
            f" Wallet: <code>{wallet}</code>"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    ib(
                        " Approve",
                        callback_data=f"withdraw:approve:{req['id']}",
                        style="success",
                        emoji_id=E_VERIFY,
                    ),
                    ib(
                        " Reject",
                        callback_data=f"withdraw:reject:{req['id']}",
                        style="danger",
                        emoji_id=E_ADMIN,
                    ),
                ]
            ]
        )

        await send_msg(
            callback.bot,
            callback.from_user.id,
            text,
            keyboard,
        )


@router.callback_query(
    F.data.startswith("withdraw:")
)
async def adm_handle_withdrawal(
    callback: types.CallbackQuery,
):

    if not await require_admin(callback):
        await safe_answer(
            callback,
            " Admin only.",
            show_alert=True,
        )
        return

    parts = callback.data.split(":")

    if len(parts) != 3:
        await safe_answer(
            callback,
            "Invalid request.",
            show_alert=True,
        )
        return

    action = parts[1]
    req_id = int(parts[2])

    status = (
        "APPROVED"
        if action == "approve"
        else "REJECTED"
    )

    req_info = (
        await db_mgr.update_withdrawal_status(
            req_id,
            status,
        )
    )

    await safe_edit(
        callback.message,
        (
            f" <b>Withdrawal #{req_id}</b>\n\n"
            f"Status: <b>{status}</b>"
        ),
    )

    await safe_answer(
        callback,
        f"Request {status.lower()}.",
    )

    if not req_info:
        return

    target_uid = req_info.get(
        "user_id"
    )

    amount = float(
        req_info.get(
            "amount",
            0,
        )
        or 0
    )

    if status == "APPROVED":

        user_text = (
            " <b>Withdrawal Approved</b>\n\n"
            f"Your withdrawal of "
            f"<code>{amount:.2f} USD</code> "
            f"has been approved."
        )

    else:

        user_text = (
            " <b>Withdrawal Rejected</b>\n\n"
            f"Your withdrawal of "
            f"<code>{amount:.2f} USD</code> "
            f"was rejected by admin."
        )

    await send_msg(
        callback.bot,
        target_uid,
        user_text,
    )


@router.callback_query(
    F.data == "adm:broadcast"
)
async def adm_trigger_broadcast(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    if not await require_admin(callback):
        await safe_answer(
            callback,
            "⛔ Admin only.",
            show_alert=True,
        )
        return

    await state.clear()
    await state.set_state(
        Form.waiting_for_broadcast_msg
    )

    await send_msg(
        callback.bot,
        callback.from_user.id,
        (
            " <b>Send broadcast message</b>\n\n"
            "The message will be sent to registered users.\n"
            "Send <b>/cancel</b> to stop."
        ),
    )

    await safe_answer(callback)


@router.callback_query(
    F.data == "adm:admins"
)
async def adm_view_admins(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    if not await require_admin(callback):
        await safe_answer(
            callback,
            " Admin only.",
            show_alert=True,
        )
        return

    await state.clear()

    admins = await db_mgr.get_admins()

    text = (
        " <b>System Admins</b>\n\n"
        + (
            "\n".join(
                f"▫️ <code>{a}</code>"
                for a in admins
            )
            if admins
            else "No admins found."
        )
    )

    await safe_edit(
        callback.message,
        text,
        InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    ib(
                        " Back",
                        callback_data="admin:panel",
                        style="primary",
                        emoji_id=E_BACK,
                    )
                ]
            ]
        ),
    )

    await safe_answer(callback)


@router.callback_query(
    F.data == "adm:addadmin"
)
async def adm_prompt_add(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    if not await require_admin(callback):
        await safe_answer(
            callback,
            " Admin only.",
            show_alert=True,
        )
        return

    await state.clear()
    await state.set_state(
        Form.waiting_for_new_admin
    )

    await send_msg(
        callback.bot,
        callback.from_user.id,
        (
            " <b>Send new admin Telegram user ID</b>\n\n"
            "Example: <code>123456789</code>"
        ),
    )

    await safe_answer(callback)


@router.callback_query(
    F.data == "adm:removeadmin"
)
async def adm_prompt_remove(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    if not await require_admin(callback):
        await safe_answer(
            callback,
            " Admin only.",
            show_alert=True,
        )
        return

    await state.clear()

    admins = await db_mgr.get_admins()

    rows = []

    for admin_id in admins:

        rows.append(
            [
                ib(
                    f" Remove {admin_id}",
                    callback_data=f"kickadmin:{admin_id}",
                    style="danger",
                    emoji_id=E_ADMIN,
                )
            ]
        )

    rows.append(
        [
            ib(
                " Back",
                callback_data="admin:panel",
                style="primary",
                emoji_id=E_BACK,
            )
        ]
    )

    await safe_edit(
        callback.message,
        " <b>Select admin to remove:</b>",
        InlineKeyboardMarkup(
            inline_keyboard=rows
        ),
    )

    await safe_answer(callback)


@router.callback_query(
    F.data.startswith("kickadmin:")
)
async def adm_process_kick(
    callback: types.CallbackQuery,
):

    if not await require_admin(callback):
        await safe_answer(
            callback,
            " Admin only.",
            show_alert=True,
        )
        return

    try:
        target = int(
            callback.data.split(
                ":",
                1,
            )[1]
        )
    except ValueError:
        await safe_answer(
            callback,
            "Invalid admin ID.",
            show_alert=True,
        )
        return

    await db_mgr.remove_admin(
        target
    )

    await safe_edit(
        callback.message,
        (
            " <b>Admin Removed</b>\n\n"
            f"User ID: <code>{target}</code>"
        ),
        InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    ib(
                        " Back",
                        callback_data="admin:panel",
                        style="primary",
                        emoji_id=E_BACK,
                    )
                ]
            ]
        ),
    )

    await safe_answer(
        callback,
        "Admin removed.",
    )


@router.callback_query(
    F.data == "adm:reqchannel"
)
async def adm_prompt_req_channel(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    if not await require_admin(callback):
        await safe_answer(
            callback,
            "⛔ Admin only.",
            show_alert=True,
        )
        return

    await state.clear()
    await state.set_state(
        Form.waiting_for_req_channel
    )

    await send_msg(
        callback.bot,
        callback.from_user.id,
        (
            " <b>Send requirements channel</b>\n\n"
            "Example:\n"
            "<code>@mychannel</code>\n"
            "or\n"
            "<code>-100123456789</code>"
        ),
    )

    await safe_answer(callback)


@router.callback_query(
    F.data.startswith("selectservice:")
)
async def adm_select_service(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    if not await require_admin(callback):
        await safe_answer(
            callback,
            "⛔ Admin only.",
            show_alert=True,
        )
        return

    values = unpack_callback(
        callback.data,
        "selectservice",
    )

    if not values:
        await safe_answer(
            callback,
            "Invalid service.",
            show_alert=True,
        )
        return

    service = values[0].upper()

    await state.update_data(
        chosen_service=service
    )

    await state.set_state(
        Form.waiting_for_nums_per_user
    )

    await send_msg(
        callback.bot,
        callback.from_user.id,
        (
            f"💥 <b>Service selected:</b> "
            f"{service}\n\n"
            f"Step 3: How many numbers per user?\n"
            f"Send an integer."
        ),
    )

    await safe_answer(callback)


@router.callback_query(
    F.data.startswith("stockbroadcast:")
)
async def adm_finalize_stock(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    if not await require_admin(callback):
        await safe_answer(
            callback,
            "⛔ Admin only.",
            show_alert=True,
        )
        return

    decision = callback.data.split(
        ":",
        1,
    )[1]

    await state.clear()

    if decision == "yes":
        await safe_edit(
            callback.message,
            (
                " <b>Stock Broadcast</b>\n\n"
                "Please send the broadcast message."
            ),
        )

        await state.set_state(
            Form.waiting_for_broadcast_msg
        )

    else:
        await safe_edit(
            callback.message,
            (
                " <b>Stock Added</b>\n\n"
                "Broadcast skipped."
            ),
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        ib(
                            " Admin Panel",
                            callback_data="admin:panel",
                            style="primary",
                            emoji_id=E_ADMIN,
                        )
                    ]
                ]
            ),
        )

    await safe_answer(callback)


@router.message(
    CommandStart()
)
async def dedicated_start_handler(
    message: types.Message,
    state: FSMContext,
):

    await state.clear()

    referrer_id = None

    try:
        parts = (
            message.text or ""
        ).split()

        if len(parts) > 1:
            clean_ref = parts[1].replace("ref_", "").strip()
            if clean_ref.isdigit():
                ref = int(clean_ref)
                if ref != message.from_user.id:
                    referrer_id = ref

    except Exception:
        referrer_id = None

    try:
        await db_mgr.register_user(
            message.from_user.id,
            referrer_id,
        )
    except Exception:
        logger.exception(
            "register_user failed"
        )

    if not await verify_dual_membership(
        message.bot,
        message.from_user.id,
    ):

        await send_msg(
            message.bot,
            message.chat.id,
            (
                f"{SYS_EMOJI}  "
                f"<b>Access Denied!</b>\n\n"
                f"Join our official channel and OTP "
                f"group first, then press "
                f"<b>TRY AGAIN / VERIFY</b>."
            ),
            generate_join_inline_keyboard(),
        )

        return

    is_admin = await db_mgr.is_admin(
        message.from_user.id
    )

    user_name = message.from_user.first_name or "User"
    
    emo_wel_left = '<tg-emoji emoji-id="6206118633370818254">✨</tg-emoji>'
    emo_wel_right = '<tg-emoji emoji-id="6206096153511990389">✨</tg-emoji>'
    emo_ult = '<tg-emoji emoji-id="6206090539989734881">🔥</tg-emoji>'
    emo_bullet = '<tg-emoji emoji-id="5775923486253912796">▪️</tg-emoji>'

    welcome_text = (
        f"{emo_wel_left} <b>Welcome to Elite OTP Engine, {user_name}!</b> {emo_wel_right}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{emo_ult} <b>The Ultimate 24/7 OTP Service</b>\n"
        f"Get high-quality numbers for any service instantly.\n\n"
        f"{emo_wel_left} <b>Why Choose Us?</b> {emo_wel_right}\n"
        f" {emo_bullet} Instant OTP Delivery\n"
        f" {emo_bullet} Premium Clean Numbers\n"
        f" {emo_bullet} Fully Automated System\n\n"
        f"{emo_ult} <i>Fast, Secure & Reliable.</i>\n\n"
        f"{emo_wel_left} <b>Please use the menu buttons below to start:</b> {emo_wel_right}"
    )

    await send_msg(
        message.bot,
        message.chat.id,
        welcome_text,
        main_permanent_keyboard(
            message.from_user.id,
            is_admin,
        ),
    )


# =========================================================
# MASTER TEXT / DOCUMENT ROUTER
# =========================================================

@router.message(
    F.text,
    ~StateFilter(
        SecurePanelFSM.waiting_for_name,
        SecurePanelFSM.waiting_for_user,
        SecurePanelFSM.waiting_for_pass,
        SecurePanelFSM.waiting_for_edit_user,
        SecurePanelFSM.waiting_for_edit_pass,
        ApiPanelFSM.waiting_for_panel_name,
        ApiPanelFSM.waiting_for_panel_url,
        ApiPanelFSM.waiting_for_edit_url,
    ),
)
async def master_text_router(message: types.Message, state: FSMContext):
    raw_text = (message.text or "").strip()
    normalized = normalize_button_text(raw_text)

    # =====================================================
    # FSM FIRST
    # =====================================================

    current_state = await state.get_state()

    if current_state and (
        current_state.startswith("SecurePanelFSM:")
        or current_state.startswith("ApiPanelFSM:")
    ):
        raise SkipHandler
    if current_state:

        if normalized in {
            "/CANCEL",
            "CANCEL",
        }:

            await state.clear()

            is_admin = await db_mgr.is_admin(
                message.from_user.id
            )

            await send_msg(
                message.bot,
                message.chat.id,
                (
                    f"{SYS_EMOJI} ❌ "
                    f"<b>Operation cancelled.</b>"
                ),
                main_permanent_keyboard(
                    message.from_user.id,
                    is_admin,
                ),
            )

            return

        if current_state == (
            Form.waiting_for_set_wallet_number.state
        ):

            wallet_num = raw_text.strip()

            if len(wallet_num) < 3:
                await send_msg(
                    message.bot,
                    message.chat.id,
                    (
                        " Invalid wallet information.\n"
                        "Please send again:"
                    ),
                )
                return

            data = await state.get_data()

            wallet_type = data.get(
                "wallet_type",
                "Unknown",
            )

            await db_mgr.set_user_wallet(
                message.from_user.id,
                wallet_type,
                wallet_num,
            )

            await state.clear()

            is_admin = await db_mgr.is_admin(
                message.from_user.id
            )

            await send_msg(
                message.bot,
                message.chat.id,
                (
                    f"{SYS_EMOJI}  "
                    f"<b>Wallet Saved</b>\n\n"
                    f"Provider: <code>{wallet_type}</code>\n"
                    f"Account: <code>{wallet_num}</code>"
                ),
                main_permanent_keyboard(
                    message.from_user.id,
                    is_admin,
                ),
            )

            return

        if current_state == (
            Form.waiting_for_withdraw_amt.state
        ):

            try:
                amount = float(raw_text)

                if amount <= 0:
                    raise ValueError

            except ValueError:

                await send_msg(
                    message.bot,
                    message.chat.id,
                    (
                        " <b>Invalid amount.</b>\n\n"
                        "Send a positive number."
                    ),
                )

                return

            user = await db_mgr.get_user(
                message.from_user.id
            )

            if not user:
                await state.clear()

                await send_msg(
                    message.bot,
                    message.chat.id,
                    " User profile not found.",
                )

                return

            try:
                min_w_raw = await db_mgr.get_config("min_withdraw")
                min_withdraw = float(min_w_raw) if min_w_raw else 0.0
            except Exception:
                min_withdraw = 0.0

            balance = float(
                user.get(
                    "balance",
                    0,
                )
                or 0
            )

            if amount < min_withdraw:

                await send_msg(
                    message.bot,
                    message.chat.id,
                    (
                        f" Minimum withdrawal is "
                        f"<code>{min_withdraw:.2f} USD</code>."
                    ),
                )

                return

            if amount > balance:

                await send_msg(
                    message.bot,
                    message.chat.id,
                    (
                        f" Insufficient balance.\n\n"
                        f"Your balance: "
                        f"<code>{balance:.4f} USD</code>"
                    ),
                )

                return

            req_id = (
                await db_mgr.create_withdraw_request(
                    message.from_user.id,
                    amount,
                    user["wallet_type"],
                    user["wallet_number"],
                )
            )

            await state.clear()

            is_admin = await db_mgr.is_admin(
                message.from_user.id
            )

            await send_msg(
                message.bot,
                message.chat.id,
                (
                    " <b>Withdrawal Submitted</b>\n\n"
                    f"Amount: <code>{amount:.2f} USD</code>\n"
                    f"Method: <code>{user['wallet_type']}</code>\n"
                    f"Wallet: <code>{user['wallet_number']}</code>\n\n"
                    " Awaiting admin approval."
                ),
                main_permanent_keyboard(
                    message.from_user.id,
                    is_admin,
                ),
            )

            admins = await db_mgr.get_admins()

            admin_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        ib(
                            " Approve",
                            callback_data=(
                                f"withdraw:approve:{req_id}"
                            ),
                            style="success",
                            emoji_id=E_VERIFY,
                        ),
                        ib(
                            " Reject",
                            callback_data=(
                                f"withdraw:reject:{req_id}"
                            ),
                            style="danger",
                            emoji_id=E_ADMIN,
                        ),
                    ]
                ]
            )

            notice = (
                " <b>New Withdrawal Request</b>\n\n"
                f"Node ID: <code>{req_id}</code>\n"
                f"User ID: <code>{message.from_user.id}</code>\n"
                f"Amount: <code>{amount}$</code>\n"
                f"Method: <code>{user['wallet_type']}</code>\n"
                f"Wallet: <code>{user['wallet_number']}</code>"
            )

            for admin_id in admins:

                await send_msg(
                    message.bot,
                    admin_id,
                    notice,
                    admin_keyboard,
                )

            return
       
        if current_state == (
            Form.waiting_for_numbers.state
        ):

            await adm_receive_numbers(
                message,
                state,
            )

            return

        if current_state == (
            Form.waiting_for_nums_per_user.state
        ):

            await adm_nums_per_user(
                message,
                state,
            )

            return

        if current_state == (
            Form.waiting_for_rate.state
        ):

            await adm_rate_per_otp(
                message,
                state,
            )

            return

        if current_state == (
            Form.waiting_for_broadcast_msg.state
        ):

            await adm_process_broadcast(
                message,
                state,
            )

            return

        if current_state == (
            Form.waiting_for_new_admin.state
        ):

            await adm_process_add_admin(
                message,
                state,
            )

            return

        if current_state == (
            Form.waiting_for_edit_support.state
        ):

            await adm_save_support(
                message,
                state,
            )

            return

        if current_state == (
            Form.waiting_for_edit_min_with.state
        ):

            await adm_save_minw(
                message,
                state,
            )

            return

        if current_state == (
            Form.waiting_for_req_channel.state
        ):

            await adm_save_req_channel(
                message,
                state,
            )

            return

        if current_state == (
            Form.waiting_for_new_service.state
        ):

            await adm_save_new_service(
                message,
                state,
            )

            return

        if current_state == Form.waiting_for_edit_service_rate.state:
            try:
                new_rate = float(raw_text)
                if new_rate < 0: raise ValueError
            except ValueError:
                return await send_msg(message.bot, message.chat.id, "🔴 <b>Invalid rate.</b>\n\nSend a valid number (e.g., 0.05):")
                
            data = await state.get_data()
            service = data.get("editing_service")
            
            if service:
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute("UPDATE categories SET rate_per_otp = ? WHERE UPPER(name) = ?", (new_rate, service.upper()))
                    await db.commit()
                
                is_admin = await db_mgr.is_admin(message.from_user.id)
                await send_msg(
                    message.bot, message.chat.id,
                    f"✅ <b>Rate Updated Successfully!</b>\n\nService: <b>{service}</b>\nNew Rate: <code>{new_rate} USD</code>",
                    main_permanent_keyboard(message.from_user.id, is_admin)
                )
            await state.clear()
            return

        

    # =====================================================
    # MEMBERSHIP
    # =====================================================

    if not await verify_dual_membership(
        message.bot,
        message.from_user.id,
    ):

        await deny_access(
            message.bot,
            message.from_user.id,
        )

        return

    # =====================================================
    # GET NUMBER
    # =====================================================

    if normalized == MENU_GET:

        categories = await db_mgr.get_categories()

        if not categories:

            is_admin = await db_mgr.is_admin(
                message.from_user.id
            )

            await send_msg(
                message.bot,
                message.chat.id,
                (
                    f"{SYS_EMOJI}  "
                    f"<b>No services are active.</b>"
                ),
                main_permanent_keyboard(
                    message.from_user.id,
                    is_admin,
                ),
            )

            return

        rows = []
        
        normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        premium = "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝗪𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝗶𝐣𝗸𝗹𝗺𝗻𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝘃𝘄𝘅𝘆𝘇"

        for category in categories:

            name = str(
                category["name"]
            ).strip()
            
            premium_name = name.upper().translate(str.maketrans(normal, premium))

            rows.append(
                [
                    ib(
                        (
                            f"{get_service_placeholder(name)} "
                            f"{premium_name}"
                        ),
                        callback_data=pack_callback(
                            "buy",
                            name,
                        ),
                        style="success",
                        emoji_id=get_service_custom_emoji_id(
                            name
                        ),
                    )
                ]
            )

        rows.append(
            [
                ib(
                    " Main Menu",
                    callback_data="menu:main",
                    style="primary",
                    emoji_id=E_BACK,
                )
            ]
        )

        await send_msg(
            message.bot,
            message.chat.id,
            (
                '<tg-emoji emoji-id="6206236607532504295">💼</tg-emoji> <b>Select service</b> <tg-emoji emoji-id="5197474438970363734">⤵️</tg-emoji>\n\n'
                'Choose the service you need:'
            ),
            InlineKeyboardMarkup(
                inline_keyboard=rows
            ),
        )

        return

    # =====================================================
    # STATUS (LIVE TRAFFIC)
    # =====================================================

    if normalized == MENU_STATUS:
        
        text = await get_live_traffic_text()
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [ib(" Refresh", callback_data="status:refresh", style="primary", emoji_id="5386367538735104399")]
            ]
        )
        
        await send_msg(
            message.bot,
            message.chat.id,
            text,
            keyboard,
        )
        return

    # =====================================================
    # ACTIVE NUMBERS (Premium Number Box Format)
    # =====================================================

    if normalized == MENU_ACTIVE:

        active = (
            await db_mgr.get_active_numbers_for_user(
                message.from_user.id
            )
        )

        is_admin = await db_mgr.is_admin(
            message.from_user.id
        )

        left_emo = '<tg-emoji emoji-id="6244779107175895852">✨</tg-emoji>'
        right_emo = '<tg-emoji emoji-id="6242179058528949496">✨</tg-emoji>'
        active_title = "𝐀𝐜𝐭𝐢𝐯𝐞 𝐍𝐮𝐦𝐛𝐞𝐫"

        if not active:

            await send_msg(
                message.bot,
                message.chat.id,
                (
                    f"{left_emo} <b>{active_title}</b> {right_emo}\n\n"
                    f"You have no active numbers."
                ),
                main_permanent_keyboard(
                    message.from_user.id,
                    is_admin,
                ),
            )

            return

        recent_active = active[-5:]
        
        normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        premium = "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝗪𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝗶𝐣𝗸𝗹𝗺𝗻𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝘃𝘄𝐱𝐲𝐳"
        
        top_icon = '<tg-emoji emoji-id="5116512467194741904">🫀</tg-emoji>'
        bottom_icon = '<tg-emoji emoji-id="4904521759161582943">🐋</tg-emoji>'
        num_emo = '<tg-emoji emoji-id="6235445786759402354">🔢</tg-emoji>'
        plat_emo = '<tg-emoji emoji-id="6158892349805040268">📱</tg-emoji>'
        
        text = f"{left_emo} <b>{active_title}</b> {right_emo}\n\n"
        
        for row in recent_active:
            c = str(row['country']).strip()
            s = str(row['service']).strip().capitalize()
            raw_num = str(row['phone_number']).strip()
            
            prem_c = c.title().translate(str.maketrans(normal, premium))
            prem_s = s.translate(str.maketrans(normal, premium))
            
            try:
                c_emo_id = get_country_custom_emoji_id(c)
                c_emo = f'<tg-emoji emoji-id="{c_emo_id}">🌍</tg-emoji>'
            except Exception:
                c_emo = '🌍'
                
            try:
                s_emo_id = get_service_custom_emoji_id(s)
                s_emo = f'<tg-emoji emoji-id="{s_emo_id}">💬</tg-emoji>'
            except Exception:
                s_emo = '💬'
                
            display_n = raw_num if raw_num.startswith('+') else f"+{raw_num}"
            
            text += (
                f"{c_emo} <b>{prem_c}</b>\n"
                f"{plat_emo} Platform: {s_emo} <b>{prem_s}</b>\n"
                f"<b>╭──────</b>{top_icon}<b>──────╮</b>\n"
                f"<b>│ </b>{num_emo} <code>{display_n}</code> {right_emo}<b> │</b>\n"
                f"<b>╰──────</b>{bottom_icon}<b>──────╯</b>\n\n"
            )

        text = text.strip() 
        
        await send_msg(
            message.bot,
            message.chat.id,
            text,
            main_permanent_keyboard(
                message.from_user.id,
                is_admin,
            ),
        )

        return

    # =====================================================
    # REFER
    # =====================================================

    if normalized == MENU_REFER:
        user = await db_mgr.get_user(message.from_user.id)
        bot_me = await message.bot.get_me()
        
        ref_link = f"https://t.me/{bot_me.username}?start=ref_{message.from_user.id}"
        is_admin = await db_mgr.is_admin(message.from_user.id)

        refs = int(user.get('referrals_count', 0))
        bal = float(user.get('balance', 0.0))

        tiers = [
            (0, "Level 1", "5294205834144795719", "🥇", 0.0002),
            (400, "Level 2", "6206222099132978580", "🥈", 0.0003),
            (600, "Level 3", "5453902265922376865", "🥉", 0.0004),
            (800, "Level 4", "5039999772300149658", "💎", 0.0006),
            (5000, "Level 5", "6125115309650089324", "👑", 0.0010)
        ]

        current_idx = 0
        for i, t in enumerate(tiers):
            if refs >= t[0]:
                current_idx = i

        cur_t = tiers[current_idx]

        tier_list_text = ""
        for i, t in enumerate(tiers):
            emo_tag = f'<tg-emoji emoji-id="{t[2]}">{t[3]}</tg-emoji>'
            if i == current_idx:
                tier_list_text += f"{emo_tag} <b>L{i+1}  ${t[4]:.4f}/OTP  ({t[0]}+ refs)  ✦</b>\n"
            else:
                tier_list_text += f"{emo_tag} L{i+1}  ${t[4]:.4f}/OTP  ({t[0]}+ refs)\n"

        crwn = '<tg-emoji emoji-id="6125115309650089324">👑</tg-emoji>'
        bar = f"[{crwn * 10}]"

        if current_idx < len(tiers) - 1:
            next_t = tiers[current_idx + 1]
            needed = next_t[0] - refs
            target_text = f'<tg-emoji emoji-id="5463274047771000031">🎯</tg-emoji> <b>{needed}</b> more referrals → <tg-emoji emoji-id="{next_t[2]}">{next_t[3]}</tg-emoji> {next_t[1]}'
            progress_text = f"{bar} {refs}/{next_t[0]}"
        else:
            target_text = f'<tg-emoji emoji-id="5463274047771000031">🎯</tg-emoji> <b>MAX RANK REACHED!</b>'
            progress_text = f"{bar} {refs}/MAX"

        text = (
            f'<tg-emoji emoji-id="6159107733824999752">🌟</tg-emoji> <b>Referral Dashboard</b>\n'
            f'══════════════════════\n'
            f'<tg-emoji emoji-id="{cur_t[2]}">{cur_t[3]}</tg-emoji> Rank: <b>{cur_t[1]}</b>\n'
            f'<tg-emoji emoji-id="5453957997418004470">👥</tg-emoji> Referrals: <b>{refs}</b>\n'
            f'<tg-emoji emoji-id="5409048419211682843">💵</tg-emoji> Balance: <b>${bal:.4f}</b>\n'
            f'<tg-emoji emoji-id="5253748096914980273">📊</tg-emoji> Progress: {progress_text}\n'
            f'{target_text}\n'
            f'──────────────────────\n'
            f'💠 <b>Commission Tiers</b>\n'
            f'──────────────────────\n'
            f'{tier_list_text}'
            f'──────────────────────\n'
            f'<tg-emoji emoji-id="5422439311196834318">💡</tg-emoji> Every OTP your referral receives\n'
            f'    = instant commission for you!\n\n'
            f'<tg-emoji emoji-id="5271604874419647061">🔗</tg-emoji> <b>Your Invite Link:</b>\n'
            f'<code>{ref_link}</code>'
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    ib(" Copy Invite Link", copy_text=ref_link, style="primary", emoji_id="5271604874419647061")
                ]
            ]
        )

        await send_msg(message.bot, message.chat.id, text, keyboard)
        return

    # =====================================================
    # WALLET
    # =====================================================

    if normalized == MENU_WALLET:

        user = await db_mgr.get_user(
            message.from_user.id
        )

        is_admin = await db_mgr.is_admin(
            message.from_user.id
        )
        
        try:
            min_w_raw = await db_mgr.get_config("min_withdraw")
            min_withdraw = float(min_w_raw) if min_w_raw else 0.10
        except Exception:
            min_withdraw = 0.10

        wallet_status = (
            f"{user['wallet_type']} "
            f"({user['wallet_number']})"
            if user.get("wallet_type")
            else "<i>Not set yet</i>"
        )

        e_title = '<tg-emoji emoji-id="6077687686607414392">💰</tg-emoji>'
        e_uid = '<tg-emoji emoji-id="5354972242629383937">🆔</tg-emoji>'
        e_bal = '<tg-emoji emoji-id="5409048419211682843">💵</tg-emoji>'
        e_withdrawn = '<tg-emoji emoji-id="5433614747381538714">📤</tg-emoji>'
        e_ref = '<tg-emoji emoji-id="5453957997418004470">👥</tg-emoji>'
        e_otp = '<tg-emoji emoji-id="6275857834127134596">📲</tg-emoji>'
        e_min_with = '<tg-emoji emoji-id="5420323339723881652">⚠️</tg-emoji>'
        e_fee = '<tg-emoji emoji-id="6156923364997862692">🎁</tg-emoji>'
        e_wallet_set = '<tg-emoji emoji-id="5472250091332993630">💳</tg-emoji>'

        text = (
            f"{e_title} <b>Wallet</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{e_uid} User ID: <code>{message.from_user.id}</code>\n"
            f"{e_bal} Balance: <b>${float(user['balance']):.4f}</b>\n"
            f"{e_withdrawn} Total Withdrawn: <b>${float(user['total_withdrawn']):.4f}</b>\n"
            f"{e_ref} Referrals: <b>{user['referrals_count']}</b>\n"
            f"{e_otp} OTP Received: <b>{user['otp_received_count']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{e_min_with} Minimum Withdraw: <b>${min_withdraw:.2f}</b>\n"
            f"{e_fee} Fee: <b>Free 0%</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{e_wallet_set} Wallet: {wallet_status}"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    ib(
                        " Withdraw",
                        callback_data="withdraw:start",
                        style="success",
                        emoji_id=E_ACTIVE,
                    ),
                    ib(
                        " Set Wallet",
                        callback_data="wallet:set",
                        style="primary",
                        emoji_id=E_ADMIN,
                    ),
                ],
                [
                    ib(
                        " Main Menu",
                        callback_data="menu:main",
                        style="primary",
                        emoji_id=E_BACK,
                    )
                ],
            ]
        )

        await send_msg(
            message.bot,
            message.chat.id,
            text,
            keyboard,
        )

        return
# =====================================================
    # LEADERBOARD
    # =====================================================
    if normalized == MENU_LEADERBOARD or raw_text == MENU_LEADERBOARD:
        
        current_name = message.from_user.first_name
        if message.from_user.last_name:
            current_name += f" {message.from_user.last_name}"
            
        async with aiosqlite.connect(DB_PATH) as db:
            try:
                await db.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
                await db.commit()
            except Exception:
                pass
            
            await db.execute("UPDATE users SET full_name = ? WHERE user_id = ?", (current_name, message.from_user.id))
            await db.commit()

            db.row_factory = aiosqlite.Row
            
            cursor = await db.execute(
                """
                SELECT o.user_id, 
                       (SELECT u.full_name FROM users u WHERE u.user_id = o.user_id) as full_name,
                       COUNT(o.phone_number) as recent_otp
                FROM otp_history o
                WHERE o.timestamp >= ? AND o.user_id != 0 AND o.user_id IS NOT NULL
                GROUP BY o.user_id
                ORDER BY recent_otp DESC
                LIMIT 10
                """,
                (BOT_START_TIME,)
            )
            top_users = await cursor.fetchall()   

        left_head = '<tg-emoji emoji-id="5470080737711502911">🏆</tg-emoji>'
        right_head = '<tg-emoji emoji-id="5451636889717062286">🔥</tg-emoji>'
        
        top_emojis = [
            '<tg-emoji emoji-id="5305763715692377402">1️⃣</tg-emoji>', '<tg-emoji emoji-id="5307907239380528763">2️⃣</tg-emoji>',
            '<tg-emoji emoji-id="5305783000095537258">3️⃣</tg-emoji>', '<tg-emoji emoji-id="5305255243104138538">4️⃣</tg-emoji>',
            '<tg-emoji emoji-id="5305288155438526869">5️⃣</tg-emoji>', '<tg-emoji emoji-id="5305642863902604489">6️⃣</tg-emoji>',
            '<tg-emoji emoji-id="5305603955793867793">7️⃣</tg-emoji>', '<tg-emoji emoji-id="5305371288825509083">8️⃣</tg-emoji>',
            '<tg-emoji emoji-id="5307703499016910744">9️⃣</tg-emoji>', '<tg-emoji emoji-id="5345804987123378599">1️⃣</tg-emoji><tg-emoji emoji-id="5305749482170758709">0️⃣</tg-emoji>'
        ]

        normal_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        premium_chars = "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝗪𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝗶𝐣𝗸𝗹𝗺𝗻𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝘃𝘄𝐱𝐲𝐳𝟎𝟏𝟮𝟑𝟒𝟓𝟔𝟕𝟖𝟗"
        font_map = str.maketrans(normal_chars, premium_chars)

        if not top_users:
            text = f"{left_head} <b>{'No active users in the leaderboard yet'.translate(font_map)}</b> {right_head}"
        else:
            text = (
                f"<b>╔══════════════════════════════════════╗</b>\n"
                f"<b>║       </b>{left_head} <b>{'TOP 10 USERS LEADERBOARD'.translate(font_map)}</b> {right_head}<b>      ║</b>\n"
                f"<b>╚══════════════════════════════════════╝</b>\n"
            )
            for i, row in enumerate(top_users):
                display_name = row['full_name'] if row['full_name'] and str(row['full_name']).strip() != "" else f"User {row['user_id']}"
                styled_name = str(display_name).translate(font_map)
                
                otp_count = row['recent_otp'] if row['recent_otp'] is not None else 0
                xp_score = otp_count * 50
                
                if otp_count >= 300:
                    rank_emo = '<tg-emoji emoji-id="5433758796289685818">👑</tg-emoji>'
                    rank_txt = "Legend".translate(font_map)
                elif otp_count >= 200:
                    rank_emo = '<tg-emoji emoji-id="5427168083074628963">💎</tg-emoji>'
                    rank_txt = "Master".translate(font_map)
                elif otp_count >= 150:
                    rank_emo = '<tg-emoji emoji-id="5438496463044752972">🔥</tg-emoji>'
                    rank_txt = "Pro".translate(font_map)
                elif otp_count >= 50:
                    rank_emo = '<tg-emoji emoji-id="5325547803936572038">⚡</tg-emoji>'
                    rank_txt = "Active".translate(font_map)
                else:
                    rank_emo = '<tg-emoji emoji-id="5363938656874673963">🌟</tg-emoji>'
                    rank_txt = "Newbie".translate(font_map)
                
                part1 = f"Key {otp_count} OTP  |  ".translate(font_map)
                part2 = f"  |  {xp_score} XP".translate(font_map)
                
                stats_text = f"{part1}{rank_emo} {rank_txt}{part2}"
                
                text += (
                    f"{top_emojis[i]}  <b>{styled_name}</b>\n"
                    f"   └─ <b>{stats_text}</b>\n"
                )

        inline_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    ib(
                        "Refresh Leaderboard".translate(font_map),
                        callback_data="refresh_leaderboard",
                        style="primary",
                        emoji_id="5976409802262190486",
                    )
                ]
            ]
        )

        try:
            await message.bot.send_message(chat_id=message.chat.id, text=text, reply_markup=inline_kb)
        except Exception:
            pass

        return

    # =====================================================
    # SUPPORT
    # =====================================================

    if normalized == MENU_SUPPORT:

        user = await db_mgr.get_user(
            message.from_user.id
        )

        support_username = str(
            user.get(
                "support_username",
                "",
            )
            or ""
        ).strip().lstrip("@")

        is_admin = await db_mgr.is_admin(
            message.from_user.id
        )

        if not support_username:

            await send_msg(
                message.bot,
                message.chat.id,
                (
                    f"{SYS_EMOJI}  "
                    f"<b>Support is not configured yet.</b>"
                ),
                main_permanent_keyboard(
                    message.from_user.id,
                    is_admin,
                ),
            )

            return

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    ib(
                        " Contact Operator",
                        url=(
                            f"https://t.me/"
                            f"{support_username}"
                        ),
                        style="primary",
                        emoji_id=E_SUPPORT,
                    )
                ],
                [
                    ib(
                        "🏠 Main Menu",
                        callback_data="menu:main",
                        style="primary",
                        emoji_id=E_BACK,
                    )
                ],
            ]
        )

        await send_msg(
            message.bot,
            message.chat.id,
            (
                f"═════《 <tg-emoji emoji-id=\"5238025132177369293\">🫂</tg-emoji> <b>SUPPORT</b> 》═════\n\n"
                f"For any issues, reach out to support."
            ),
            keyboard,
        )

        return

    # =====================================================
    # ADMIN PANEL
    # =====================================================

    if normalized == MENU_ADMIN:

        is_admin = await db_mgr.is_admin(
            message.from_user.id
        )

        if not is_admin:

            await send_msg(
                message.bot,
                message.chat.id,
                " <b>Admin access required.</b>",
            )

            return

        await send_msg(
            message.bot,
            message.chat.id,
            (
                f"{SYS_EMOJI}  "
                f"<b>Administrative Command Hub</b>"
            ),
            admin_inline_panel(),
        )

        return

    # =====================================================
    # UNKNOWN TEXT
    # =====================================================

    is_admin = await db_mgr.is_admin(
        message.from_user.id
    )

    await send_msg(
        message.bot,
        message.chat.id,
        (
            f"{SYS_EMOJI}  "
            f"<b>Please use the menu buttons below.</b>"
        ),
        main_permanent_keyboard(
            message.from_user.id,
            is_admin,
        ),
    )

# =========================================================
# DOCUMENT ROUTER
# =========================================================

@router.message(
    F.document
)
async def document_router(
    message: types.Message,
    state: FSMContext,
):

    current_state = await state.get_state()

    if current_state != (
        Form.waiting_for_numbers.state
    ):
        await send_msg(
            message.bot,
            message.chat.id,
            (
                "📄 I received the file, but "
                "no number-upload operation is active."
            ),
        )
        return

    if not await db_mgr.is_admin(
        message.from_user.id
    ):
        await send_msg(
            message.bot,
            message.chat.id,
            "⛔ Admin only.",
        )
        await state.clear()
        return

    await adm_receive_numbers(
        message,
        state,
    )


async def adm_receive_numbers(
    message: types.Message,
    state: FSMContext,
):

    content = ""

    if message.document:

        try:
            downloaded = await message.bot.download(
                message.document
            )

            if downloaded is not None:
                content = (
                    downloaded.getvalue()
                    .decode(
                        "utf-8",
                        errors="ignore",
                    )
                )

        except Exception:
            logger.exception(
                "Number file download failed"
            )

            await send_msg(
                message.bot,
                message.chat.id,
                (
                    "🔴 Could not read the file.\n"
                    "Please upload TXT/CSV again."
                ),
            )

            return

    elif message.text:

        content = message.text

    parsed = re.findall(
        r"\+?\d{7,}",
        content,
    )

    cleaned = []

    seen = set()

    for number in parsed:

        clean = (
            number
            .replace("+", "")
            .strip()
        )

        if (
            len(clean) >= 7
            and clean not in seen
        ):
            seen.add(clean)
            cleaned.append(clean)

    if not cleaned:

        await send_msg(
            message.bot,
            message.chat.id,
            (
                "🔴 <b>No valid numbers found.</b>\n\n"
                "Send numbers again:"
            ),
        )

        return

    await state.update_data(
        raw_numbers=cleaned
    )

    service_list = await db_mgr.get_services()

    if not service_list:

        service_list = [
            "Tiktok",
            "Facebook",
            "Telegram",
            "Instagram",
            "Paypal",
        ]

    rows = []
    
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    premium = "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝗪𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝗶𝐣𝗸𝗹𝗺𝗻𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝘃𝘄𝗫𝘆𝘇"

    for service in service_list:

        service = str(
            service
        ).strip()
        
        premium_service = service.upper().translate(str.maketrans(normal, premium))

        rows.append(
            [
                ib(
                    (
                        f"{get_service_placeholder(service)} "
                        f"{premium_service}"
                    ),
                    callback_data=pack_callback(
                        "selectservice",
                        service,
                    ),
                    style="primary",
                    emoji_id=get_service_custom_emoji_id(
                        service
                    ),
                )
            ]
        )

    await send_msg(
        message.bot,
        message.chat.id,
        (
            " <b>Numbers Parsed Successfully</b>\n\n"
            f"Unique numbers: "
            f"<code>{len(cleaned)}</code>\n\n"
            "<b>Step 2:</b> Select service:"
        ),
        InlineKeyboardMarkup(
            inline_keyboard=rows
        ),
    )

    await state.set_state(
        Form.waiting_for_service
    )


async def adm_nums_per_user(
    message: types.Message,
    state: FSMContext,
):

    if not message.text:
        await send_msg(
            message.bot,
            message.chat.id,
            "🔴 Send an integer.",
        )
        return

    value = message.text.strip()

    if not value.isdigit():

        await send_msg(
            message.bot,
            message.chat.id,
            (
                "🔴 <b>Invalid quota.</b>\n\n"
                "Send a valid integer:"
            ),
        )

        return

    quota = int(value)

    if quota <= 0:

        await send_msg(
            message.bot,
            message.chat.id,
            "🔴 Quota must be greater than zero.",
        )

        return

    await state.update_data(
        per_user=quota
    )

    await send_msg(
        message.bot,
        message.chat.id,
        (
            "<b>Step 4</b>\n\n"
            "Send rate per successful OTP in USD.\n\n"
            "Example: <code>0.05</code>"
        ),
    )

    await state.set_state(
        Form.waiting_for_rate
    )


async def adm_rate_per_otp(
    message: types.Message,
    state: FSMContext,
):

    if not message.text:
        return

    try:
        rate = float(message.text.strip())
        if rate < 0: raise ValueError
    except ValueError:
        await send_msg(
            message.bot, message.chat.id,
            "🔴 <b>Invalid rate.</b>\n\nExample: <code>0.05</code>"
        )
        return

    data = await state.get_data()
    nums = data.get("raw_numbers", [])
    service = data.get("chosen_service")
    per_user = data.get("per_user")

    if not nums or not service or not per_user:
        await state.clear()
        await send_msg(
            message.bot, message.chat.id,
            "❌ Add-number session expired.\nPlease start again."
        )
        return

    await db_mgr.save_category(service, per_user, rate)

    base_countries = set()
    num_to_base = {}
    
    for number in nums:
        try:
            c = resolve_universal_country(number)
            if not c or c == "UNKNOWN": c = f"Zone (+{number[:3]})"
        except Exception:
            c = f"Zone (+{number[:3]})"
            
        base_countries.add(c)
        num_to_base[number] = c

    country_suffixes = {}
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            for bc in base_countries:
                bc_upper = bc.upper()
                cursor = await db.execute(
                    "SELECT DISTINCT country FROM numbers_pool WHERE UPPER(service) = UPPER(?) AND UPPER(country) LIKE ?",
                    (service, f"{bc_upper}%")
                )
                rows = await cursor.fetchall()
                existing = [r[0].upper() for r in rows]

                if not existing:
                    country_suffixes[bc] = bc
                else:
                    max_suffix = 0
                    has_base = False
                    for ex in existing:
                        if ex == bc_upper:
                            has_base = True
                        else:
                            suffix_str = ex[len(bc_upper):].strip()
                            if suffix_str.isdigit():
                                max_suffix = max(max_suffix, int(suffix_str))
                    
                    if has_base and max_suffix == 0:
                        country_suffixes[bc] = f"{bc} 1"
                    elif has_base or max_suffix > 0:
                        country_suffixes[bc] = f"{bc} {max_suffix + 1}"
                    else:
                        country_suffixes[bc] = bc
    except Exception as e:
        logger.error(f"Batch naming error: {e}")
        for bc in base_countries:
            country_suffixes[bc] = bc

    insert_payload = []
    for number in nums:
        bc = num_to_base[number]
        final_country = country_suffixes[bc]
        insert_payload.append((number, final_country, service.upper()))

    await db_mgr.bulk_insert_numbers(insert_payload)
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """CREATE TABLE IF NOT EXISTS file_rates 
                (country_batch TEXT, service TEXT, rate REAL, PRIMARY KEY(country_batch, service))"""
            )
            for final_country in set(country_suffixes.values()):
                await db.execute(
                    """INSERT OR REPLACE INTO file_rates 
                    (country_batch, service, rate) VALUES (?, ?, ?)""", 
                    (final_country.upper(), service.upper(), rate)
                )
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to save file rate: {e}")

    # 🎨 Country ar Service er emoji & name resolve kora
    country_name = str(list(set(country_suffixes.values()))[0]).strip().title()
    service_name = service.strip().capitalize()
    rate_val = f"${rate:.3f}"

    c_emo_id = get_country_custom_emoji_id(country_name)
    c_emoji_tag = f'<tg-emoji emoji-id="{c_emo_id}">🇸🇾</tg-emoji>'

    s_emo_id = get_service_custom_emoji_id(service_name)
    s_emoji_tag = f'<tg-emoji emoji-id="{s_emo_id}">🚫</tg-emoji>'

    # 🔥 Per user line shoho updated gorgeous box design format
    auto_broadcast_text = (
        f'╭━━━〔 <tg-emoji emoji-id="5841521509608198453">🆕</tg-emoji> <b>NEW STOCK</b> 〕━━━╮\n'
        f'┃ <tg-emoji emoji-id="5224450179368767019">🌎</tg-emoji> <b>Country</b> <tg-emoji emoji-id="6158862632926319619">👉</tg-emoji> {country_name} {c_emoji_tag}\n'
        f'┃ <tg-emoji emoji-id="5798678738384195183">💎</tg-emoji> <b>Service</b>  <tg-emoji emoji-id="6158862632926319619">👉</tg-emoji>  {service_name} {s_emoji_tag}\n'
        f'┃ <tg-emoji emoji-id="5994308618906770092">💰</tg-emoji> <b>OTP Rate</b> <tg-emoji emoji-id="6158862632926319619">👉</tg-emoji> <b>{rate_val}</b> <tg-emoji emoji-id="5424972470023104089">🔥</tg-emoji>\n'
        f'┃ <tg-emoji emoji-id="5841276284155467413">🔤</tg-emoji> Per user <tg-emoji emoji-id="6158862632926319619">👉</tg-emoji> {per_user} <tg-emoji emoji-id="5305699699204837855">🍀</tg-emoji>\n'
        f'╰━━━━━━━━━━━━━━━━━━━━╯'
    )
    
    await state.update_data(
        auto_broadcast_msg=auto_broadcast_text,
        broadcast_service=service
    )

    confirm_text = (
        "✅ <b>Stock Added Successfully</b>\n\n"
        f"💥 Service: <code>{service}</code>\n"
        f"👤 Per user: <code>{per_user}</code>\n"
        f"💵 Rate: <code>{rate}$</code>\n"
        f"📱 Added: <code>{len(insert_payload)}</code>\n\n"
        "Do you want to AUTO-BROADCAST the new stock?"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                ib("📢 Auto Broadcast", callback_data="autobroadcast:yes", style="success", emoji_id=E_VERIFY),
                ib("🔕 No Broadcast", callback_data="autobroadcast:no", style="danger", emoji_id=E_ADMIN),
            ]
        ]
    )

    await send_msg(message.bot, message.chat.id, confirm_text, keyboard)
    await state.set_state(Form.waiting_for_broadcast_decision)

async def adm_process_broadcast(
    message: types.Message,
    state: FSMContext,
):

    if not await db_mgr.is_admin(
        message.from_user.id
    ):
        await state.clear()
        return

    await state.clear()

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM users"
        ) as cursor:
            rows = await cursor.fetchall()

    sent = 0
    failed = 0

    for row in rows:
        user_id = row[0]

        try:
            await message.send_copy(chat_id=user_id)
            sent += 1

        except TelegramForbiddenError:
            failed += 1
        except Exception:
            failed += 1

    emo_delivered = '<tg-emoji emoji-id="6235253239080555488">✅</tg-emoji>'
    emo_failed = '<tg-emoji emoji-id="6206029267986289507">❌</tg-emoji>'
    emo_total = '<tg-emoji emoji-id="6206343625232619150">👥</tg-emoji>'

    await send_msg(
        message.bot,
        message.chat.id,
        (
            " <b>Broadcast Completed</b>\n\n"
            f"{emo_delivered} <b>Delivered:</b> <code>{sent}</code>\n"
            f"{emo_failed} <b>Failed:</b> <code>{failed}</code>\n"
            f"{emo_total} <b>Total:</b> <code>{len(rows)}</code>"
        ),
        admin_inline_panel(),
    )


@router.message(Form.waiting_for_broadcast_msg)
async def broadcast_media_router(
    message: types.Message,
    state: FSMContext,
):
    if message.text:
        normalized = normalize_button_text(message.text.strip())
        if normalized in {"/CANCEL", "CANCEL"}:
            await state.clear()
            is_admin = await db_mgr.is_admin(message.from_user.id)
            await send_msg(
                message.bot,
                message.chat.id,
                f"{SYS_EMOJI} ❌ <b>Operation cancelled.</b>",
                main_permanent_keyboard(message.from_user.id, is_admin),
            )
            return

    await adm_process_broadcast(message, state)


async def adm_process_add_admin(
    message: types.Message,
    state: FSMContext,
):

    if not message.text:
        return

    value = message.text.strip()

    if not value.isdigit():

        await send_msg(
            message.bot,
            message.chat.id,
            (
                " User ID must be an integer.\n"
                "Try again:"
            ),
        )

        return

    target = int(value)

    await db_mgr.add_admin(
        target
    )

    await state.clear()

    await send_msg(
        message.bot,
        message.chat.id,
        (
            " <b>Admin Added</b>\n\n"
            f"User ID: <code>{target}</code>"
        ),
        admin_inline_panel(),
    )


async def adm_save_support(
    message: types.Message,
    state: FSMContext,
):

    raw = (
        message.text or ""
    ).strip()

    cleaned = re.sub(
        r"^(https?://)?"
        r"(t\.me/|telegram\.me/)?"
        r"@?",
        "",
        raw,
        flags=re.IGNORECASE,
    ).strip().strip("/")

    if not cleaned:

        await send_msg(
            message.bot,
            message.chat.id,
            (
                " Invalid username.\n"
                "Example: <code>support</code>"
            ),
        )

        return

    await db_mgr.set_global_setting(
        "support_username",
        cleaned,
    )

    await state.clear()

    await send_msg(
        message.bot,
        message.chat.id,
        (
            " <b>Support Updated</b>\n\n"
            f"Username: <code>{cleaned}</code>"
        ),
        admin_inline_panel(),
    )


async def adm_save_minw(
    message: types.Message,
    state: FSMContext,
):

    try:
        value = float(
            message.text.strip()
        )

        if value < 0:
            raise ValueError

    except Exception:

        await send_msg(
            message.bot,
            message.chat.id,
            (
                " Invalid amount.\n"
                "Example: <code>5</code>"
            ),
        )

        return

    await db_mgr.set_global_setting(
        "min_withdraw",
        value,
    )

    await state.clear()

    await send_msg(
        message.bot,
        message.chat.id,
        (
            " <b>Minimum withdrawal updated</b>\n\n"
            f"New value: <code>{value:.2f}</code>"
        ),
        admin_inline_panel(),
    )


async def adm_save_req_channel(
    message: types.Message,
    state: FSMContext,
):

    value = (
        message.text or ""
    ).strip()

    if not value:

        await send_msg(
            message.bot,
            message.chat.id,
            " Channel value cannot be empty.",
        )

        return

    await db_mgr.set_global_setting(
        "req_channel",
        value,
    )

    await state.clear()

    await send_msg(
        message.bot,
        message.chat.id,
        (
            " <b>Requirements Channel Updated</b>\n\n"
            f"Target: <code>{value}</code>"
        ),
        admin_inline_panel(),
    )


async def adm_save_new_service(
    message: types.Message,
    state: FSMContext,
):

    name = (
        message.text or ""
    ).strip()

    if not name:

        await send_msg(
            message.bot,
            message.chat.id,
            (
                " Please send a valid service name.\n"
                "Example: <code>Snapchat</code>"
            ),
        )

        return

    await db_mgr.add_service(
        name
    )

    await state.clear()

    await send_msg(
        message.bot,
        message.chat.id,
        (
            " <b>Service Added</b>\n\n"
            f"Service: <code>{name}</code>"
        ),
        admin_inline_panel(),
    )


@router.callback_query(F.data.startswith("autobroadcast:"))
async def process_instant_auto_broadcast(callback: types.CallbackQuery, state: FSMContext):
    
    if not await db_mgr.is_admin(callback.from_user.id):
        await safe_answer(callback, "Admin only", show_alert=True)
        return
        
    decision = callback.data.split(":")[1]
    
    if decision == "no":
        await state.clear()
        await safe_edit(callback.message, "✅ Stock added silently. No broadcast sent.", admin_inline_panel())
        return
        
    data = await state.get_data()
    broadcast_text = data.get("auto_broadcast_msg")
    broadcast_service = data.get("broadcast_service")
    
    if not broadcast_text or not broadcast_service:
        await safe_answer(callback, "Session expired.", show_alert=True)
        await state.clear()
        return
        
    await safe_edit(callback.message, "⏳ <b>Broadcasting... please wait.</b>")
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            
    sent = 0
    failed = 0
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            ib(
                " GET NUMBER NOW", 
                callback_data=pack_callback("buy", broadcast_service), 
                style="success", 
                emoji_id=E_GET
            )
        ]]
    )
    
    for row in rows:
        uid = row[0]
        try:
            await callback.bot.send_message(
                chat_id=uid, 
                text=broadcast_text, 
                reply_markup=kb, 
                parse_mode="HTML"
            )
            sent += 1
        except Exception:
            failed += 1
            
    emo_delivered = '<tg-emoji emoji-id="6235253239080555488">✅</tg-emoji>'
    emo_failed = '<tg-emoji emoji-id="6206029267986289507">❌</tg-emoji>'
    
    finish_text = (
        f"📢 <b>Auto Broadcast Completed</b>\n\n"
        f"{emo_delivered} <b>Delivered:</b> <code>{sent}</code>\n"
        f"{emo_failed} <b>Failed:</b> <code>{failed}</code>"
    )
    
    await safe_edit(callback.message, finish_text, admin_inline_panel())
    await state.clear()


import datetime
from collections import defaultdict


async def get_live_traffic_text():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        time_col = "timestamp" 
        
        cursor = await db.execute(f"SELECT COUNT(*) as total FROM otp_history WHERE datetime({time_col}) >= datetime('now', '-10 minute')")
        row = await cursor.fetchone()
        total_otps = row['total'] if row and row['total'] else 0

        query = f"""
            SELECT 
                n.country as db_country,
                o.phone_number,
                o.service as service_name
            FROM otp_history o
            LEFT JOIN numbers_pool n ON o.phone_number = n.phone_number
            WHERE datetime(o.{time_col}) >= datetime('now', '-10 minute')
        """
        cursor = await db.execute(query)
        recent_otps = await cursor.fetchall()

    stats_dict = defaultdict(int)

    for r in recent_otps:
        service = str(r['service_name']).upper()
        phone = str(r['phone_number']).replace('+', '')
        
        if r['db_country']:
            batch = str(r['db_country']).title()
        else:
            batch = "Unknown Zone"
            for prefix in sorted(GLOBAL_COUNTRY_MAP.keys(), key=lambda x: len(str(x)), reverse=True):
                if phone.startswith(str(prefix)):
                    batch = str(GLOBAL_COUNTRY_MAP[prefix]).title()
                    break
                    
        stats_dict[(batch, service)] += 1

    stats = [{"batch_name": k[0], "service_name": k[1], "otp_count": v} for k, v in stats_dict.items()]
    stats = sorted(stats, key=lambda x: x["otp_count"], reverse=True)[:5]

    emo_live = '<tg-emoji emoji-id="5264919878082509254">🔴</tg-emoji>'
    emo_win = '<tg-emoji emoji-id="5269539162654010758">🥇</tg-emoji>'
    emo_res = '<tg-emoji emoji-id="5257980374868311346">⏱️</tg-emoji>'
    emo_top_c = '<tg-emoji emoji-id="5228875876879318811">🏆</tg-emoji>'
    emo_globe = '<tg-emoji emoji-id="5314361729117855941">🌍</tg-emoji>'
    emo_arr = '<tg-emoji emoji-id="5416117059207572332">➡️</tg-emoji>'
    emo_time = '<tg-emoji emoji-id="5382194935057372936">🕘</tg-emoji>'

    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    premium = "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝗪𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝗶𝐣𝗸𝗹𝗺𝗻𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝘃𝘄𝘅𝘆𝘇"

    bdt_time = (datetime.datetime.utcnow() + datetime.timedelta(hours=6)).strftime("%I:%M:%S %p")

    if total_otps == 0 or not stats:
        return (
            f"{emo_live} <b>Live Traffic</b>\n\n"
            f"{emo_win} <b>Window:</b> Last 10 minutes\n"
            f"{emo_res} <b>Results Sent:</b> 0\n\n"
            f"No OTPs received in the last 10 minutes.\n\n"
            f"{emo_time} <b>Last Update:</b> {bdt_time}"
        )

    top_batch = str(stats[0]['batch_name']).title()
    top_service = str(stats[0]['service_name']).upper()

    try:
        top_c_emo_id = get_country_custom_emoji_id(top_batch)
        top_c_emo = f'<tg-emoji emoji-id="{top_c_emo_id}">🌍</tg-emoji>'
    except Exception: 
        top_c_emo = '🌍'
    
    try:
        top_s_emo_id = get_service_custom_emoji_id(top_service)
        top_s_emo = f'<tg-emoji emoji-id="{top_s_emo_id}">💬</tg-emoji>'
    except Exception: 
        top_s_emo = '💬'

    text = (
        f"{emo_live} <b>Live Traffic</b>\n"
        f"{emo_win} <b>Window:</b> Last 10 minutes\n"
        f"{emo_res} <b>Results Sent:</b> {total_otps}\n"
        f"{emo_top_c} <b>Top Country:</b> {top_c_emo} <b>{top_batch}</b> {top_s_emo}\n\n"
        f"{emo_globe} <b>Top Countries:</b>\n"
    )

    for idx, row in enumerate(stats, 1):
        batch = str(row['batch_name']).title()
        service = str(row['service_name']).upper()
        
        count = row['otp_count']
        percent = (count / total_otps) * 100 if total_otps > 0 else 0

        try:
            c_emo_id = get_country_custom_emoji_id(batch)
            c_emo = f'<tg-emoji emoji-id="{c_emo_id}">🌍</tg-emoji>'
        except Exception: 
            c_emo = '🌍'
        
        try:
            s_emo_id = get_service_custom_emoji_id(service)
            s_emo = f'<tg-emoji emoji-id="{s_emo_id}">💬</tg-emoji>'
        except Exception: 
            s_emo = '💬'

        text += f"{idx}. {c_emo} <b>{batch}</b> {emo_arr} <b>{percent:.1f}%</b> {s_emo}\n"

    text += f"\n{emo_time} <b>Last Update:</b> {bdt_time}"
    return text


@router.callback_query(F.data == "status:refresh")
async def process_status_refresh(callback: types.CallbackQuery):
    text = await get_live_traffic_text()
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [ib(" Refresh", callback_data="status:refresh", style="primary", emoji_id="5386367538735104399")]
        ]
    )
    
    await safe_edit(callback.message, text, keyboard)
    await safe_answer(callback, "Live Traffic Updated!", show_alert=False)


@router.callback_query(lambda c: c.data == "refresh_leaderboard")
async def process_refresh_leaderboard(callback_query):
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        cursor = await db.execute(
            """
            SELECT o.user_id, 
                   (SELECT u.full_name FROM users u WHERE u.user_id = o.user_id) as full_name,
                   COUNT(o.phone_number) as recent_otp
            FROM otp_history o
            WHERE o.timestamp >= ? AND o.user_id != 0 AND o.user_id IS NOT NULL
            GROUP BY o.user_id
            ORDER BY recent_otp DESC
            LIMIT 10
            """,
            (BOT_START_TIME,)
        )
        top_users = await cursor.fetchall()

    left_head = '<tg-emoji emoji-id="5470080737711502911">🏆</tg-emoji>'
    right_head = '<tg-emoji emoji-id="5451636889717062286">🔥</tg-emoji>'
    
    top_emojis = [
        '<tg-emoji emoji-id="5305763715692377402">1️⃣</tg-emoji>', '<tg-emoji emoji-id="5307907239380528763">2️⃣</tg-emoji>',
        '<tg-emoji emoji-id="5305783000095537258">3️⃣</tg-emoji>', '<tg-emoji emoji-id="5305255243104138538">4️⃣</tg-emoji>',
        '<tg-emoji emoji-id="5305288155438526869">5️⃣</tg-emoji>', '<tg-emoji emoji-id="5305642863902604489">6️⃣</tg-emoji>',
        '<tg-emoji emoji-id="5305603955793867793">7️⃣</tg-emoji>', '<tg-emoji emoji-id="5305371288825509083">8️⃣</tg-emoji>',
        '<tg-emoji emoji-id="5307703499016910744">9️⃣</tg-emoji>', '<tg-emoji emoji-id="5345804987123378599">1️⃣</tg-emoji><tg-emoji emoji-id="5305749482170758709">0️⃣</tg-emoji>'
    ]

    normal_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    premium_chars = "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"
    font_map = str.maketrans(normal_chars, premium_chars)

    if not top_users:
        text = f"{left_head} <b>{'No active users in the leaderboard yet'.translate(font_map)}</b> {right_head}"
    else:
        text = (
            f"<b>╔══════════════════════════════════════╗</b>\n"
            f"<b>║       </b>{left_head} <b>{'TOP 10 USERS LEADERBOARD'.translate(font_map)}</b> {right_head}<b>      ║</b>\n"
            f"<b>╚══════════════════════════════════════╝</b>\n"
        )
        for i, row in enumerate(top_users):
            display_name = row['full_name'] if row['full_name'] and str(row['full_name']).strip() != "" else f"User {row['user_id']}"
            styled_name = str(display_name).translate(font_map)
            
            otp_count = row['recent_otp'] if row['recent_otp'] is not None else 0
            xp_score = otp_count * 50
            
            if otp_count >= 300:
                rank_emo = '<tg-emoji emoji-id="5433758796289685818">👑</tg-emoji>'
                rank_txt = "Legend".translate(font_map)
            elif otp_count >= 200:
                rank_emo = '<tg-emoji emoji-id="5427168083074628963">💎</tg-emoji>'
                rank_txt = "Master".translate(font_map)
            elif otp_count >= 150:
                rank_emo = '<tg-emoji emoji-id="5438496463044752972">🔥</tg-emoji>'
                rank_txt = "Pro".translate(font_map)
            elif otp_count >= 50:
                rank_emo = '<tg-emoji emoji-id="5325547803936572038">⚡</tg-emoji>'
                rank_txt = "Active".translate(font_map)
            else:
                rank_emo = '<tg-emoji emoji-id="5363938656874673963">🌟</tg-emoji>'
                rank_txt = "Newbie".translate(font_map)
            
            part1 = f"Key {otp_count} OTP  |  ".translate(font_map)
            part2 = f"  |  {xp_score} XP".translate(font_map)
            
            stats_text = f"{part1}{rank_emo} {rank_txt}{part2}"
            
            text += (
                f"{top_emojis[i]}  <b>{styled_name}</b>\n"
                f"   └─ <b>{stats_text}</b>\n"
            )

    inline_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                ib(
                    "Refreshed Just Now".translate(font_map),
                    callback_data="refresh_leaderboard",
                    style="primary",
                    emoji_id="5976409802262190486",
                )
            ]
        ]
    )

    try:
        await callback_query.message.edit_text(text, reply_markup=inline_kb)
        await callback_query.answer("Leaderboard Updated! 🚀")
    except Exception:
        await callback_query.answer("Leaderboard is already up to date! ✅")

# =====================================================
# ADMIN ANTI-ABUSE CONTROLS
# =====================================================

@router.callback_query(F.data.startswith("sys_unban:"))
async def process_sys_unban(callback: types.CallbackQuery):
    is_admin = await db_mgr.is_admin(callback.from_user.id)
    if not is_admin:
        return await callback.answer("You are not an admin!", show_alert=True)
        
    target_id = callback.data.split(":")[1]
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned = 0, wasted_count = 0 WHERE user_id = ?", (target_id,))
        await db.commit()
        
    await callback.answer(f"User {target_id} has been unbanned successfully!", show_alert=True)
    
    try:
        await callback.message.edit_text(callback.message.html_text + "\n\n✅ <b>RESOLVED: User Unbanned.</b>")
    except Exception:
        pass

@router.callback_query(F.data.startswith("sys_notice:"))
async def process_sys_notice_start(callback: types.CallbackQuery, state: FSMContext):
    is_admin = await db_mgr.is_admin(callback.from_user.id)
    if not is_admin:
        return await callback.answer("You are not an admin!", show_alert=True)
        
    target_id = callback.data.split(":")[1]
    
    await state.update_data(target_user_id=target_id)
    await state.set_state(AdminNoticeState.waiting_for_message)
    
    await callback.message.reply("📝 Please type the notice message you want to send to this banned user. \n(Or type /cancel to abort)")
    await callback.answer()

@router.message(AdminNoticeState.waiting_for_message)
async def process_sys_notice_send(message: types.Message, state: FSMContext):
    if message.text and message.text.lower() == "/cancel":
        await state.clear()
        return await message.reply("Action cancelled.")
        
    data = await state.get_data()
    target_id = data.get("target_user_id")
    
    notice_text = (
        f'<tg-emoji emoji-id="5420323339723881652">⚠️</tg-emoji> <b>Message from Admin:</b>\n\n'
        f'{message.html_text}'
    )
    
    try:
        await message.bot.send_message(chat_id=target_id, text=notice_text)
        await message.reply(f"✅ Notice sent successfully to user {target_id}.")
    except Exception:
        await message.reply("❌ Failed to send notice. User might have blocked the bot.")
        
    await state.clear()

