"""Names of fill types for marker names. The game's own names are packed in its files, so the
common ones are listed here (German in the editor's catalog); others are made readable from
their ID ("SUGARBEET_CUT" → "Sugarbeet cut", "farmSilo" → "Farm silo")."""

import re

from autodrive_editor.i18n import tr


def _names() -> dict[str, str]:
    """Looked up on each call, so the names follow the language."""

    return {
        "WATER": tr("Water"),
        "DIESEL": tr("Diesel"),
        "STRAW": tr("Straw"),
        "MANURE": tr("Manure"),
        "LIQUIDMANURE": tr("Slurry"),
        "DIGESTATE": tr("Digestate"),
        "MILK": tr("Milk"),
        "SEEDS": tr("Seeds"),
        "FERTILIZER": tr("Fertilizer"),
        "LIQUIDFERTILIZER": tr("Liquid fertilizer"),
        "HERBICIDE": tr("Herbicide"),
        "LIME": tr("Lime"),
        "WHEAT": tr("Wheat"),
        "BARLEY": tr("Barley"),
        "OAT": tr("Oat"),
        "RYE": tr("Rye"),
        "CANOLA": tr("Canola"),
        "SUNFLOWER": tr("Sunflowers"),
        "SOYBEAN": tr("Soybeans"),
        "MAIZE": tr("Maize"),
        "POTATO": tr("Potatoes"),
        "SUGARBEET": tr("Sugar beet"),
        "SUGARCANE": tr("Sugarcane"),
        "COTTON": tr("Cotton"),
        "RICE": tr("Rice"),
        "GRASS_WINDROW": tr("Grass"),
        "DRYGRASS_WINDROW": tr("Hay"),
        "SILAGE": tr("Silage"),
        "CHAFF": tr("Chaff"),
        "WOODCHIPS": tr("Wood chips"),
        "FORAGE": tr("Total mixed ration"),
        "PIGFOOD": tr("Pig food"),
        "MINERAL_FEED": tr("Mineral feed"),
        "EMPTYPALLET": tr("Empty pallets"),
        "CARTON": tr("Cartons"),
        "SUGAR": tr("Sugar"),
        "FLOUR": tr("Flour"),
        "BREAD": tr("Bread"),
        "CAKE": tr("Cake"),
        "BUTTER": tr("Butter"),
        "CHEESE": tr("Cheese"),
        "EGG": tr("Eggs"),
        "WOOL": tr("Wool"),
        "HONEY": tr("Honey"),
        "BOARDS": tr("Boards"),
        "STONE": tr("Stones"),
        "SAND": tr("Sand"),
        "GRAVEL": tr("Gravel"),
        "COMPOST": tr("Compost"),
        "GARBAGE": tr("Garbage"),
        "GRAPE": tr("Grapes"),
        "OLIVE": tr("Olives"),
        "APPLE": tr("Apples"),
        "CHERRY": tr("Cherries"),
        "PEACH": tr("Peaches"),
        "PEARS": tr("Pears"),
        "APRICOTS": tr("Apricots"),
        "TOMATO": tr("Tomatoes"),
        "STRAWBERRY": tr("Strawberries"),
        "METHANE": tr("Methane"),
        "WHISKEY": tr("Whiskey"),
        "VODKA": tr("Vodka"),
        "RUM": tr("Rum"),
    }


def fill_type_name(fill_type: str) -> str:
    names = _names()

    if fill_type in names:
        return names[fill_type]

    words = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", fill_type).replace("_", " ").split()

    return " ".join(words).capitalize()
